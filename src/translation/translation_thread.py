import threading
import asyncio
import os
import pysrt
from queue import Queue

from src.utils.file_utils import ensure_backup_dir, get_output_path
from src.domain.errors import ExternalServiceError
from src.infrastructure.prompt.json_prompt_provider import JsonPromptProvider
from src.infrastructure.translation.ollama_translation_client import OllamaTranslationClient

class TranslationThread(threading.Thread):
    def __init__(self, file_path, source_lang, target_lang, model_name, parallel_requests, progress_callback, complete_callback, debug_mode=False, replace_original=False, use_alt_prompt=False, prompt_provider=None, translation_client=None, coordinator=None):
        threading.Thread.__init__(self)
        self.file_path = file_path
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.model_name = model_name
        self.parallel_requests = parallel_requests
        self.progress_callback = progress_callback
        self.complete_callback = complete_callback
        self.debug_mode = debug_mode
        self.app = None
        self.replace_original = replace_original
        self.use_alt_prompt = use_alt_prompt
        self.prompt_provider = prompt_provider or JsonPromptProvider(
            os.path.join(os.path.dirname(__file__), "prompts.json")
        )
        self.translation_client = translation_client or OllamaTranslationClient(
            "http://localhost:11434/v1/chat/completions"
        )
        self.coordinator = coordinator

    def set_app(self, app):
        """設置對 App 實例的引用"""
        self.app = app
        
    def run(self):
        subs = pysrt.open(self.file_path)
        total_subs = len(subs)
        batch_size = int(self.parallel_requests)

        # 如果是取代原始檔案模式，先創建備份
        if self.replace_original:
            try:
                backup_path = os.path.join(os.path.dirname(self.file_path), 'backup')
                ensure_backup_dir(backup_path)
                backup_file = os.path.join(backup_path, os.path.basename(self.file_path))
                import shutil
                shutil.copy2(self.file_path, backup_file)
            except Exception as e:
                self.complete_callback(f"警告：無法創建備份檔案：{str(e)}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for i in range(0, total_subs, batch_size):
            batch = subs[i:i+batch_size]
            texts = [sub.text for sub in batch]
            results = loop.run_until_complete(self.translate_batch_async(texts))
            
            for sub, result in zip(batch, results):
                if result:
                    if self.debug_mode:
                        print(f"\n原始文本: {sub.text}")
                        print(f"翻譯結果: {result}")
                        print("-" * 50)
                    sub.text = result
                
            self.progress_callback(min(i+batch_size, total_subs), total_subs)

        loop.close()

        output_path = self.get_output_path()
        if output_path:  # 只有在有效的輸出路徑時才保存
            subs.save(output_path, encoding='utf-8')
            self.complete_callback(f"翻譯完成 | 檔案已成功保存為: {output_path}")
        else:
            self.complete_callback(f"已跳過檔案: {self.file_path}")

    async def translate_batch_async(self, texts):
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, self.fetch, text) for text in texts]
        return await asyncio.gather(*tasks)

    def fetch(self, text):
        try:
            return self.translation_client.translate_text(
                text=text,
                target_lang=self.target_lang,
                model_name=self.model_name,
                system_prompt=self._get_system_prompt(),
            )
        except ExternalServiceError:
            return None

    def _get_system_prompt(self):
        return self.prompt_provider.get_prompt(use_alt_prompt=self.use_alt_prompt)


    def get_output_path(self):
        """獲取輸出路徑"""
        base_path = get_output_path(self.file_path, self.target_lang, self.replace_original)
        
        # 檢查檔案是否存在
        if os.path.exists(base_path) and not self.replace_original:
            # 發送訊息到主線程處理檔案衝突
            response = self.handle_file_conflict(base_path)
            if response == "rename":
                # 自動重新命名，加上數字後綴
                dir_name, file_name = os.path.split(self.file_path)
                name, ext = os.path.splitext(file_name)
                from src.utils.file_utils import get_language_suffix
                lang_suffix = get_language_suffix(self.target_lang)
                
                counter = 1
                while True:
                    new_path = os.path.join(dir_name, f"{name}{lang_suffix}_{counter}{ext}")
                    if not os.path.exists(new_path):
                        return new_path
                    counter += 1
            elif response == "skip":
                return None
            # response == "overwrite" 則使用原始路徑
        
        return base_path

    def handle_file_conflict(self, file_path):
        """處理檔案衝突"""
        # 使用 Queue 在線程間通信
        queue = Queue()
        
        # 請求主線程顯示對話框
        self.progress_callback(-1, -1, {
            "type": "file_conflict",
            "path": file_path,
            "queue": queue
        })
        
        # 等待使用者回應
        return queue.get()
