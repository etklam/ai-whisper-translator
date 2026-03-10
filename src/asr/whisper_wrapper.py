#!/usr/bin/env python3
"""
Whisper.cpp ctypes wrapper
Provides Python bindings for the whisper.cpp C library.
"""

import ctypes
import os
from typing import Optional, List, Tuple
from dataclasses import dataclass

from src.asr.utils.constants import WHISPER_SAMPLE_RATE


# Enums
class WhisperSamplingStrategy(ctypes.c_int):
    WHISPER_SAMPLING_GREEDY = 0
    WHISPER_SAMPLING_BEAM_SEARCH = 1


class WhisperAlignmentHeadsPreset(ctypes.c_int):
    WHISPER_AHEADS_NONE = 0
    WHISPER_AHEADS_N_TOP_MOST = 1
    WHISPER_AHEADS_CUSTOM = 2
    WHISPER_AHEADS_TINY_EN = 3
    WHISPER_AHEADS_TINY = 4
    WHISPER_AHEADS_BASE_EN = 5
    WHISPER_AHEADS_BASE = 6
    WHISPER_AHEADS_SMALL_EN = 7
    WHISPER_AHEADS_SMALL = 8
    WHISPER_AHEADS_MEDIUM_EN = 9
    WHISPER_AHEADS_MEDIUM = 10
    WHISPER_AHEADS_LARGE_V1 = 11
    WHISPER_AHEADS_LARGE_V2 = 12
    WHISPER_AHEADS_LARGE_V3 = 13
    WHISPER_AHEADS_LARGE_V3_TURBO = 14


# Callback types
WHISPER_NEW_SEGMENT_CALLBACK = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p
)
WHISPER_PROGRESS_CALLBACK = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p
)
WHISPER_ENCODER_BEGIN_CALLBACK = ctypes.CFUNCTYPE(
    ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
)
WHISPER_LOGITS_FILTER_CALLBACK = ctypes.CFUNCTYPE(
    None,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_void_p,
)
GGML_ABORT_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p)


# Structures
class WhisperAhead(ctypes.Structure):
    _fields_ = [
        ("n_text_layer", ctypes.c_int),
        ("n_head", ctypes.c_int),
    ]


class WhisperAheads(ctypes.Structure):
    _fields_ = [
        ("n_heads", ctypes.c_size_t),
        ("heads", ctypes.POINTER(WhisperAhead)),
    ]


class WhisperContextParams(ctypes.Structure):
    _fields_ = [
        ("use_gpu", ctypes.c_bool),
        ("flash_attn", ctypes.c_bool),
        ("gpu_device", ctypes.c_int),
        ("dtw_token_timestamps", ctypes.c_bool),
        ("dtw_aheads_preset", WhisperAlignmentHeadsPreset),
        ("dtw_n_top", ctypes.c_int),
        ("dtw_aheads", WhisperAheads),
        ("dtw_mem_size", ctypes.c_size_t),
    ]


class WhisperTokenData(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_int32),
        ("tid", ctypes.c_int32),
        ("p", ctypes.c_float),
        ("plog", ctypes.c_float),
        ("pt", ctypes.c_float),
        ("ptsum", ctypes.c_float),
        ("t0", ctypes.c_int64),
        ("t1", ctypes.c_int64),
        ("t_dtw", ctypes.c_int64),
        ("vlen", ctypes.c_float),
    ]


class WhisperVadParams(ctypes.Structure):
    _fields_ = [
        ("threshold", ctypes.c_float),
        ("min_speech_duration_ms", ctypes.c_int),
        ("min_silence_duration_ms", ctypes.c_int),
        ("max_speech_duration_s", ctypes.c_float),
        ("speech_pad_ms", ctypes.c_int),
        ("samples_overlap", ctypes.c_float),
    ]


class WhisperGreedyParams(ctypes.Structure):
    _fields_ = [("best_of", ctypes.c_int)]


class WhisperBeamSearchParams(ctypes.Structure):
    _fields_ = [
        ("beam_size", ctypes.c_int),
        ("patience", ctypes.c_float),
    ]


class WhisperFullParams(ctypes.Structure):
    _fields_ = [
        ("strategy", WhisperSamplingStrategy),
        ("n_threads", ctypes.c_int),
        ("n_max_text_ctx", ctypes.c_int),
        ("offset_ms", ctypes.c_int),
        ("duration_ms", ctypes.c_int),
        ("translate", ctypes.c_bool),
        ("no_context", ctypes.c_bool),
        ("no_timestamps", ctypes.c_bool),
        ("single_segment", ctypes.c_bool),
        ("print_special", ctypes.c_bool),
        ("print_progress", ctypes.c_bool),
        ("print_realtime", ctypes.c_bool),
        ("print_timestamps", ctypes.c_bool),
        ("token_timestamps", ctypes.c_bool),
        ("thold_pt", ctypes.c_float),
        ("thold_ptsum", ctypes.c_float),
        ("max_len", ctypes.c_int),
        ("split_on_word", ctypes.c_bool),
        ("max_tokens", ctypes.c_int),
        ("debug_mode", ctypes.c_bool),
        ("audio_ctx", ctypes.c_int),
        ("tdrz_enable", ctypes.c_bool),
        ("suppress_regex", ctypes.c_char_p),
        ("initial_prompt", ctypes.c_char_p),
        ("carry_initial_prompt", ctypes.c_bool),
        ("prompt_tokens", ctypes.POINTER(ctypes.c_int32)),
        ("prompt_n_tokens", ctypes.c_int),
        ("language", ctypes.c_char_p),
        ("detect_language", ctypes.c_bool),
        ("suppress_blank", ctypes.c_bool),
        ("suppress_nst", ctypes.c_bool),
        ("temperature", ctypes.c_float),
        ("max_initial_ts", ctypes.c_float),
        ("length_penalty", ctypes.c_float),
        ("temperature_inc", ctypes.c_float),
        ("entropy_thold", ctypes.c_float),
        ("logprob_thold", ctypes.c_float),
        ("no_speech_thold", ctypes.c_float),
        ("greedy", WhisperGreedyParams),
        ("beam_search", WhisperBeamSearchParams),
        ("new_segment_callback", WHISPER_NEW_SEGMENT_CALLBACK),
        ("new_segment_callback_user_data", ctypes.c_void_p),
        ("progress_callback", WHISPER_PROGRESS_CALLBACK),
        ("progress_callback_user_data", ctypes.c_void_p),
        ("encoder_begin_callback", WHISPER_ENCODER_BEGIN_CALLBACK),
        ("encoder_begin_callback_user_data", ctypes.c_void_p),
        ("abort_callback", GGML_ABORT_CALLBACK),
        ("abort_callback_user_data", ctypes.c_void_p),
        ("logits_filter_callback", WHISPER_LOGITS_FILTER_CALLBACK),
        ("logits_filter_callback_user_data", ctypes.c_void_p),
        ("grammar_rules", ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))),
        ("n_grammar_rules", ctypes.c_size_t),
        ("i_start_rule", ctypes.c_size_t),
        ("grammar_penalty", ctypes.c_float),
        ("vad", ctypes.c_bool),
        ("vad_model_path", ctypes.c_char_p),
        ("vad_params", WhisperVadParams),
    ]


class WhisperTimings(ctypes.Structure):
    _fields_ = [
        ("sample_ms", ctypes.c_float),
        ("encode_ms", ctypes.c_float),
        ("decode_ms", ctypes.c_float),
        ("batchd_ms", ctypes.c_float),
        ("prompt_ms", ctypes.c_float),
    ]


# Opaque types
whisper_context_p = ctypes.c_void_p
whisper_state_p = ctypes.c_void_p


@dataclass
class WhisperSegment:
    """Represents a transcribed text segment."""
    text: str
    start: int  # start time in milliseconds
    end: int  # end time in milliseconds
    no_speech_prob: float = 0.0


class WhisperWrapper:
    """
    Python wrapper for whisper.cpp library using ctypes.
    """

    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize the whisper.cpp library.

        Args:
            library_path: Path to libwhisper.dylib (or .so/.dll). If None, tries default locations.
        """
        if library_path is None:
            # Try default locations
            default_paths = [
                "whisper.cpp/build/src/libwhisper.dylib",
                "whisper.cpp/build/src/libwhisper.so",
                "whisper.cpp/build/src/whisper.dll",
                "/usr/local/lib/libwhisper.dylib",
                "/usr/local/lib/libwhisper.so",
            ]
            for path in default_paths:
                if os.path.exists(path):
                    library_path = path
                    break
            else:
                raise FileNotFoundError(
                    "Could not find whisper library. "
                    "Please specify library_path or build whisper.cpp."
                )

        self.lib = ctypes.CDLL(library_path)

        # Check whisper.cpp version for ABI compatibility
        self._check_version()

        # Set up function prototypes
        self._setup_functions()

    def _setup_functions(self):
        """Set up ctypes function prototypes for whisper functions."""

        # Version
        self.lib.whisper_version.argtypes = []
        self.lib.whisper_version.restype = ctypes.c_char_p

        # Context init
        self.lib.whisper_init_from_file_with_params.argtypes = [
            ctypes.c_char_p,
            WhisperContextParams,
        ]
        self.lib.whisper_init_from_file_with_params.restype = whisper_context_p

        self.lib.whisper_free.argtypes = [whisper_context_p]
        self.lib.whisper_free.restype = None

        # Default params
        self.lib.whisper_context_default_params.argtypes = []
        self.lib.whisper_context_default_params.restype = WhisperContextParams

        self.lib.whisper_full_default_params.argtypes = [WhisperSamplingStrategy]
        self.lib.whisper_full_default_params.restype = WhisperFullParams

        # Full transcription
        self.lib.whisper_full.argtypes = [
            whisper_context_p,
            WhisperFullParams,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
        ]
        self.lib.whisper_full.restype = ctypes.c_int

        # Segments
        self.lib.whisper_full_n_segments.argtypes = [whisper_context_p]
        self.lib.whisper_full_n_segments.restype = ctypes.c_int

        self.lib.whisper_full_get_segment_text.argtypes = [whisper_context_p, ctypes.c_int]
        self.lib.whisper_full_get_segment_text.restype = ctypes.c_char_p

        self.lib.whisper_full_get_segment_t0.argtypes = [whisper_context_p, ctypes.c_int]
        self.lib.whisper_full_get_segment_t0.restype = ctypes.c_int64

        self.lib.whisper_full_get_segment_t1.argtypes = [whisper_context_p, ctypes.c_int]
        self.lib.whisper_full_get_segment_t1.restype = ctypes.c_int64

        self.lib.whisper_full_get_segment_no_speech_prob.argtypes = [
            whisper_context_p, ctypes.c_int
        ]
        self.lib.whisper_full_get_segment_no_speech_prob.restype = ctypes.c_float

        # Language
        self.lib.whisper_lang_id.argtypes = [ctypes.c_char_p]
        self.lib.whisper_lang_id.restype = ctypes.c_int

        self.lib.whisper_lang_str.argtypes = [ctypes.c_int]
        self.lib.whisper_lang_str.restype = ctypes.c_char_p

        self.lib.whisper_full_lang_id.argtypes = [whisper_context_p]
        self.lib.whisper_full_lang_id.restype = ctypes.c_int

        # Timings
        self.lib.whisper_print_timings.argtypes = [whisper_context_p]
        self.lib.whisper_print_timings.restype = None

        # System info
        self.lib.whisper_print_system_info.argtypes = []
        self.lib.whisper_print_system_info.restype = ctypes.c_char_p

    def get_version(self) -> str:
        """Get the whisper.cpp version."""
        return self.lib.whisper_version().decode("utf-8")

    def _check_version(self):
        """Check whisper.cpp version for ABI compatibility.
        
        Raises:
            RuntimeError: If version is not compatible with expected 1.8.3
        """
        version = self.get_version()
        logger.info(f"Detected whisper.cpp version: {version}")
        
        # Pin to 1.8.3 for ABI compatibility
        EXPECTED_VERSION = "1.8.3"
        if not version.startswith("1.8"):
            raise RuntimeError(
                f"whisper.cpp version {version} is not compatible. "
                f"Expected version 1.8.x for ABI compatibility. "
                f"Please build whisper.cpp from commit: v1.8.3 or use a compatible version."
            )
        
        logger.info(f"whisper.cpp version {version} is compatible with expected {EXPECTED_VERSION}")

    def get_system_info(self) -> str:
        """Get system information."""
        return self.lib.whisper_print_system_info().decode("utf-8")

    def init_context(self, model_path: str, use_gpu: bool = False) -> whisper_context_p:
        """
        Initialize a whisper context from a model file.

        Args:
            model_path: Path to the .ggml model file
            use_gpu: Whether to use GPU acceleration

        Returns:
            Whisper context pointer
        """
        cparams = self.lib.whisper_context_default_params()
        cparams.use_gpu = use_gpu

        model_path_bytes = model_path.encode("utf-8")
        ctx = self.lib.whisper_init_from_file_with_params(model_path_bytes, cparams)

        if ctx is None:
            raise RuntimeError(f"Failed to initialize whisper context from {model_path}")

        return ctx

    def free_context(self, ctx: whisper_context_p):
        """Free a whisper context."""
        if ctx is not None:
            self.lib.whisper_free(ctx)

    def get_full_params(
        self,
        strategy: int = WhisperSamplingStrategy.WHISPER_SAMPLING_GREEDY,
        language: Optional[str] = None,
        n_threads: int = 4,
        translate: bool = False,
        no_timestamps: bool = False,
        print_progress: bool = False,
    ) -> WhisperFullParams:
        """
        Get default full parameters with optional modifications.

        Args:
            strategy: Sampling strategy (greedy or beam search)
            language: Language code (e.g., 'en', 'es', 'auto')
            n_threads: Number of threads to use
            translate: Whether to translate to English
            no_timestamps: Whether to disable timestamps
            print_progress: Whether to print progress

        Returns:
            WhisperFullParams structure
        """
        params = self.lib.whisper_full_default_params(strategy)

        params.n_threads = n_threads
        params.translate = translate
        params.no_timestamps = no_timestamps
        params.print_progress = print_progress

        if language:
            if language.lower() == "auto":
                params.detect_language = True
                params.language = None
            else:
                lang_bytes = language.encode("utf-8")
                params.language = lang_bytes
                params.detect_language = False
        else:
            # Handle None as auto-detect
            params.detect_language = True
            params.language = None

        return params

    def transcribe(
        self,
        ctx: whisper_context_p,
        audio_samples: ctypes.Array,
        n_samples: int,
        params: WhisperFullParams,
    ) -> List[WhisperSegment]:
        """
        Transcribe audio samples.

        Args:
            ctx: Whisper context
            audio_samples: Array of float32 audio samples (16kHz)
            n_samples: Number of samples
            params: Transcription parameters

        Returns:
            List of WhisperSegment objects
        """
        result = self.lib.whisper_full(ctx, params, audio_samples, n_samples)

        if result != 0:
            raise RuntimeError(f"whisper_full failed with error code {result}")

        # Extract segments
        n_segments = self.lib.whisper_full_n_segments(ctx)
        segments = []

        for i in range(n_segments):
            text = self.lib.whisper_full_get_segment_text(ctx, i).decode("utf-8")
            t0 = self.lib.whisper_full_get_segment_t0(ctx, i)
            t1 = self.lib.whisper_full_get_segment_t1(ctx, i)
            no_speech_prob = self.lib.whisper_full_get_segment_no_speech_prob(ctx, i)

            segments.append(
                WhisperSegment(text=text, start=t0, end=t1, no_speech_prob=no_speech_prob)
            )

        return segments

    def get_detected_language(self, ctx: whisper_context_p) -> Optional[str]:
        """
        Get the detected language from the context.

        Args:
            ctx: Whisper context

        Returns:
            Language code (e.g., 'en') or None
        """
        lang_id = self.lib.whisper_full_lang_id(ctx)
        if lang_id < 0:
            return None
        lang_str = self.lib.whisper_lang_str(lang_id)
        if lang_str:
            return lang_str.decode("utf-8")
        return None

    def print_timings(self, ctx: whisper_context_p):
        """Print performance timings to stdout."""
        self.lib.whisper_print_timings(ctx)
