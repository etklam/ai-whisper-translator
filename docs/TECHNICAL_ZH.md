# 技術文件（繁體中文）

本文件提供維護者與開發者使用。

## 1. 範圍與現況

- 執行環境為 Python。
- 主入口：`main.py` → `src/main.py`。
- GUI：`src/gui/app.py`（單頁流程：佇列 + AI 引擎面板）。
- application/domain/infrastructure 分層已在實作中。
- `src/*.ts` 為骨架，未接入實際執行流程。
- 套件管理：uv 優先，pip 相容。

## 1.1 開發進度（截至 2026-03-14）

已完成並可用：
- whisper.cpp ASR 轉錄
- OpenAI 相容端點翻譯（預設 Ollama）與 LibreTranslate
- 摘要功能（ASR 逐字稿摘要）
- 翻譯批次標記請求
- 佇列式 ASR 處理（可選翻譯/摘要）
- GPU 後端與 CPU fallback
- 多格式輸出（SRT/TXT/JSON/Verbose）
- `.config` 設定持久化

進行中 / 下一步：
- 移除舊版翻譯 UI 並整合流程
- macOS/Windows 打包
- 擴充 GUI/ASR 測試覆蓋

## 2. 執行期架構

啟動流程：

1. `main.py`
2. `src.main.main()`
3. `build_default_coordinator()` 建立：
   - `PysrtSubtitleRepository`
   - `OllamaTranslationClient`
   - `JsonPromptProvider`
4. 建立 GUI `App`
5. 將 `event_sink` 綁定到 GUI

高層流程：
- GUI 收集輸入與設定
- 翻譯（coordinator 路徑）建立 `TranslationRequest`
- 同時保留 legacy `TranslationThread`

## 3. 模組職責

### Application
- `src/application/`
  - `models.py`：請求模型（`TranslationRequest`, `ASRRequest`）
  - `events.py`：進度事件
  - `translation_coordinator.py`：翻譯協調 + 批次標記
  - `asr_coordinator.py`：ASR 協調

### Domain
- `src/domain/`：服務協定與錯誤

### Infrastructure
- `src/infrastructure/`
  - `translation/ollama_translation_client.py`：OpenAI 相容端點
  - `translation/libretranslate_client.py`：LibreTranslate
  - `prompt/json_prompt_provider.py`：提示詞 JSON
  - `subtitles/pysrt_subtitle_repository.py`

### ASR
- `src/asr/`：whisper.cpp 綁定、轉錄、下載、格式轉換

### GUI
- `src/gui/app.py`：單頁 UI（左側佇列 / AI 引擎面板切換）

### Legacy
- `src/translation/translation_thread.py`

## 4. 端到端流程

### 佇列（ASR → 摘要 → 翻譯）

1. 加入音訊/影片檔或 YouTube URL
2. 執行 ASR 產出 SRT
3. （可選）摘要產出 `.summary.txt`
4. （可選）翻譯 SRT

### 翻譯（Coordinator）

- GUI 建立 `TranslationRequest`
- coordinator 執行批次標記翻譯
- `ExternalServiceError` 觸發重試

### Legacy Thread

- `TranslationThread` 仍存在並處理部分流程

## 5. 設定與預設值

### 翻譯 / AI 引擎
- OpenAI 相容端點預設：`http://localhost:11434/v1/chat/completions`
- 環境變數：`OPENAI_COMPAT_ENDPOINT`、`OPENAI_API_KEY`
- LibreTranslate：`LIBRETRANSLATE_ENDPOINT`
- 提示詞：`src/translation/prompts.json`
- GUI 覆寫：`.config`

### ASR
- whisper.cpp library：`whisper.cpp/build/src/libwhisper.dylib`
- 模型預設：`whisper.cpp/models/ggml-base.bin`
- GPU 後端：auto/metal/cuda/hip/vulkan/opencl/cpu
- 輸出格式：srt/txt/json/verbose

### 設定持久化
- `.config` 保存 UI 與提示詞覆寫（依語言）

## 6. 提示詞系統

- `JsonPromptProvider` 支援多語 key：
  - `default_prompt_{lang}` / `alt_prompt_{lang}`
  - `summary_prompt_{lang}`
- GUI 覆寫優先，儲存在 `.config`
- `use_alt_prompt` 切換替代提示詞

## 7. ASR 系統

- whisper.cpp 已內建於專案
- ctypes 綁定 + runtime manifest
- 音訊轉換：16kHz mono PCM float32

## 8. 輸出與衝突處理

- `src/utils/file_utils.py` 計算輸出路徑
- Replace 模式會備份到 `backup/`
- GUI 提供覆蓋/重新命名/跳過

## 9. 錯誤與重試

- API 失敗轉為 `ExternalServiceError`
- coordinator 只對服務錯誤重試
- 摘要失敗會記錄並繼續佇列

## 10. 測試

建議（uv）：

```bash
uv run pytest -v
```

備援（pip）：

```bash
$env:PYTHONPATH='.'; pytest -v
```

## 11. 打包

詳見 `docs/packaging.md`。
