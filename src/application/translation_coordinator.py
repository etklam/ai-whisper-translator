import logging
import os
import shutil
import threading
from dataclasses import dataclass
import re

import pysrt

from src.application.events import ProgressEvent
from src.domain.errors import ExternalServiceError
from src.utils.file_utils import ensure_backup_dir

logger = logging.getLogger(__name__)


@dataclass
class ExecutionSummary:
    total_files: int
    successful_files: int
    failed_files: int


class TranslationCoordinator:
    def __init__(self, subtitle_repo, translation_client, prompt_provider, event_sink=None):
        self.subtitle_repo = subtitle_repo
        self.translation_client = translation_client
        self.prompt_provider = prompt_provider
        self.event_sink = event_sink
        logger.debug(
            "TranslationCoordinator initialized repo=%s client=%s prompt_provider=%s event_sink=%s",
            type(subtitle_repo).__name__,
            type(translation_client).__name__,
            type(prompt_provider).__name__,
            bool(event_sink),
        )

    def run(self, request):
        successful = 0
        failed = 0
        total = len(request.file_paths)
        logger.info(
            "Coordinator run started total_files=%s target_lang=%s model=%s retries=%s",
            total,
            request.target_lang,
            request.model_name,
            request.max_retries,
        )
        for index, file_path in enumerate(request.file_paths, start=1):
            logger.debug("Processing file index=%s/%s path=%s", index, total, file_path)
            system_prompt = self.prompt_provider.get_prompt(use_alt_prompt=request.use_alt_prompt)
            file_failed = False

            try:
                if request.clean_before_translate:
                    logger.debug(
                        "Cleaning SRT before translate path=%s replace_original=%s",
                        file_path,
                        request.replace_original,
                    )
                    self.subtitle_repo.clean_srt_file(
                        file_path,
                        create_backup=request.replace_original,
                    )
                elif request.replace_original:
                    backup_dir = os.path.join(os.path.dirname(file_path), "backup")
                    ensure_backup_dir(backup_dir)
                    backup_path = os.path.join(backup_dir, os.path.basename(file_path))
                    shutil.copy2(file_path, backup_path)
                    logger.debug("Backup created for replace mode source=%s backup=%s", file_path, backup_path)

                subs = pysrt.open(file_path)
                logger.info(
                    "Translating subtitles file=%s count=%s parallel=%s",
                    file_path,
                    len(subs),
                    request.parallel_requests,
                )

                batch_size = max(1, int(request.parallel_requests))
                batch_size = min(batch_size, 10)
                for start in range(0, len(subs), batch_size):
                    batch = subs[start:start + batch_size]
                    texts = [sub.text for sub in batch]
                    for attempt in range(request.max_retries + 1):
                        try:
                            logger.debug(
                                "Translate batch file=%s start=%s size=%s attempt=%s",
                                file_path,
                                start,
                                len(batch),
                                attempt + 1,
                            )
                            translated_batch = self._translate_batch(
                                texts=texts,
                                source_lang=request.source_lang,
                                target_lang=request.target_lang,
                                model_name=request.model_name,
                                system_prompt=system_prompt,
                            )
                            if translated_batch is None:
                                translated_batch = [
                                    self.translation_client.translate_text(
                                        text=single,
                                        source_lang=request.source_lang,
                                        target_lang=request.target_lang,
                                        model_name=request.model_name,
                                        system_prompt=system_prompt,
                                    )
                                    for single in texts
                                ]
                            for sub, translated in zip(batch, translated_batch):
                                sub.text = translated
                            break
                        except ExternalServiceError as exc:
                            logger.warning(
                                "External service error file=%s batch_start=%s attempt=%s/%s error=%s",
                                file_path,
                                start,
                                attempt + 1,
                                request.max_retries + 1,
                                exc,
                            )
                            if attempt == request.max_retries:
                                file_failed = True
                                logger.error("Batch translation failed after all retries file=%s start=%s", file_path, start)
                                break
                        except Exception as exc:
                            file_failed = True
                            logger.exception(
                                "Unexpected translation failure file=%s batch_start=%s error=%s",
                                file_path,
                                start,
                                exc,
                            )
                            break

                    if file_failed:
                        logger.warning("Stopping translation for file=%s due to batch failure", file_path)
                        break

                # Only save if all subtitles were successfully translated
                if not file_failed:
                    output_path = self.subtitle_repo.get_output_path(
                        file_path,
                        request.target_lang,
                        replace_original=request.replace_original,
                    )
                    subs.save(output_path, encoding="utf-8")
                    logger.info("Saved translated file source=%s output=%s", file_path, output_path)
                else:
                    logger.warning("Skipping save for file=%s due to translation failures", file_path)
            except Exception:
                file_failed = True
                logger.exception("File translation failed path=%s", file_path)

            if file_failed:
                failed += 1
            else:
                successful += 1

            if self.event_sink:
                self.event_sink(
                    ProgressEvent(
                        current=index,
                        total=total,
                        message=f"Processed {index}/{total}",
                    )
                )
            logger.debug(
                "Progress emitted index=%s/%s successful=%s failed=%s",
                index,
                total,
                successful,
                failed,
            )

        summary = ExecutionSummary(
            total_files=len(request.file_paths),
            successful_files=successful,
            failed_files=failed,
        )
        logger.info(
            "Coordinator run completed total=%s successful=%s failed=%s",
            summary.total_files,
            summary.successful_files,
            summary.failed_files,
        )
        return summary

    def _translate_batch(self, texts, source_lang, target_lang, model_name, system_prompt):
        if len(texts) == 1:
            translated = self.translation_client.translate_text(
                text=texts[0],
                source_lang=source_lang,
                target_lang=target_lang,
                model_name=model_name,
                system_prompt=system_prompt,
            )
            return [translated]

        prompt_text = self._build_tagged_prompt(texts)
        response = self.translation_client.translate_text(
            text=prompt_text,
            source_lang=source_lang,
            target_lang=target_lang,
            model_name=model_name,
            system_prompt=system_prompt,
        )
        parsed = self._parse_tagged_response(response, len(texts))
        if parsed is None:
            return None
        return parsed

    @staticmethod
    def _build_tagged_prompt(texts):
        lines = [
            "Return translations with the same tags, preserving the tags exactly.",
            "Do not add, remove, or reorder any tags.",
            "Each tag must appear exactly once in the output.",
        ]
        for idx, text in enumerate(texts, start=1):
            lines.append(f"<<<S{idx}>>>")
            lines.append(text)
        return "\n".join(lines)

    @staticmethod
    def _parse_tagged_response(response, expected_count):
        if not response:
            return None
        tag_pattern = re.compile(r"<<<S(\d+)>>>")
        matches = list(tag_pattern.finditer(response))
        if not matches:
            return None
        results = [None for _ in range(expected_count)]
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(response)
            idx = int(match.group(1)) - 1
            if 0 <= idx < expected_count:
                results[idx] = response[start:end].strip()
        if any(r is None for r in results):
            return None
        return results

    def run_async(self, request, callback=None):
        def _run():
            logger.debug("Async run thread started")
            summary = self.run(request)
            if callback:
                logger.debug("Invoking async callback")
                callback(summary)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        logger.debug("Async translation thread launched thread=%s", thread.name)
        return thread
