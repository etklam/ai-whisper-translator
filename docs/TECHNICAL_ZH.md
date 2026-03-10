# 技術文件（繁體中文）

本文件給維護者與開發者使用。

## 1. 範圍與現況

- 目前正式執行路徑是 Python 應用。
- 主入口為 [`main.py`](../main.py)，再呼叫 [`src/main.py`](../src/main.py)。
- GUI 主要在 [`src/gui/app.py`](../src/gui/app.py)。
- 專案已具備 application/domain/infrastructure 分層，但仍在整合期。
- `src/*.ts` 的 TypeScript 檔目前為草稿骨架，未接入現行執行流程。
- 套件管理已支援 uv 優先且保留 pip 相容：
  - `pyproject.toml` + `uv.lock` 供 uv 同步與執行
  - `requirements.txt` 保留給 pip 安裝路徑

## 2. 執行期架構

啟動流程：

1. `main.py`
2. `src.main.main()`
3. `build_default_coordinator()` 建立：
   - `PysrtSubtitleRepository`
   - `OllamaTranslationClient`
   - `JsonPromptProvider`
4. 建立 GUI `App(coordinator=...)`
5. 將 `coordinator.event_sink` 綁定到 `app.on_coordinator_event`

高層資料流：

- GUI 收集檔案與設定。
- GUI 建立 `TranslationRequest`。
- `TranslationCoordinator.run_async()` 在背景執行並發送進度事件。

## 3. 模組職責

### 應用層（Application Layer）
- `src/application/`
  - `models.py`：請求模型（`TranslationRequest`）
  - `events.py`：進度事件（`ProgressEvent`）
  - `translation_coordinator.py`：翻譯流程協調、重試與彙總
  - `asr_coordinator.py`：ASR 語音轉錄協調與 whisper.cpp 整合

### 領域層（Domain Layer）
- `src/domain/`
  - 服務介面與領域錯誤定義

### 基礎設施層（Infrastructure Layer）
- `src/infrastructure/`
  - `translation/ollama_translation_client.py`：呼叫 Ollama `/v1/chat/completions`
  - `prompt/json_prompt_provider.py`：讀取 JSON 提示詞
  - `subtitles/pysrt_subtitle_repository.py`：字幕檔操作適配層

### ASR 層（新增）
- `src/asr/`
  - `whisper_wrapper.py`：whisper.cpp Python ctypes 綁定
  - `whisper_transcriber.py`：Whisper 轉錄器協調
  - `audio_downloader.py`：YouTube 音訊下載（使用 yt-dlp）
  - `audio_converter.py`：音訊格式轉換為 16kHz 單聲道 PCM float32
  - `utils/`：ASR 專用工具（日誌、常數、輔助函數）

### GUI 層
- `src/gui/`
  - `app.py`：Tkinter 介面，採用標籤頁架構（翻譯 + ASR）
  - 檔案匯入、事件綁定、進度呈現

### 舊版層（Legacy Layer）
- `src/translation/`
  - 舊版 thread 字幕翻譯流程（`TranslationThread`）

### 工具層
- `src/utils/`
  - 輸出命名、備份建立、字幕清理工具

## 4. 端到端流程

### 翻譯流程（GUI + Coordinator）

1. 使用者在 UI（翻譯標籤頁）匯入 SRT 檔案。
2. 設定來源語言、目標語言、模型、並行數。
3. 觸發翻譯。
4. 產生 `TranslationRequest` 並交給 coordinator。
5. coordinator 對 `ExternalServiceError` 進行重試（最多 `max_retries`）。
6. coordinator 發送 `ProgressEvent`。
7. GUI 更新進度條與完成狀態。

### ASR 流程（語音轉錄）

1. 使用者切換到 ASR 標籤頁。
2. 使用者選擇音訊檔案，或輸入 YouTube URL 並下載。
3. 使用者設定 Whisper 模型、GPU 後端、語言、輸出格式。
4. 使用者啟動轉錄。
5. 產生 `ASRRequest` 並交給 ASRCoordinator。
6. ASRCoordinator 初始化 WhisperWrapper 並載入模型。
7. 音訊轉換為 16kHz 單聲道 PCM float32 格式。
8. whisper.cpp 處理音訊並產生轉錄段落。
9. ASRCoordinator 格式化輸出（SRT/TXT/JSON/Verbose）並儲存到檔案。
10. ASRCoordinator 發送 `ProgressEvent`。
11. GUI 更新進度條與完成狀態。

### 舊版 Thread 流程

`TranslationThread` 仍保留「分批翻譯字幕、檔名衝突處理、輸出存檔」的完整邏輯，目前與新版流程並存。

## 5. 設定與預設值

### 翻譯配置
- Ollama 端點（預設）：`http://localhost:11434/v1/chat/completions`
- 主程序環境變數：`main.py` 內設定 `OLLAMA_NUM_PARALLEL=5`
- UI 預設並行數：`10`
- `TranslationRequest.max_retries`：預設 `1`
- 提示詞檔案：`src/translation/prompts.json`

### ASR 配置
- Whisper 函式庫路徑：`whisper.cpp/build/src/libwhisper.dylib`（自動偵測）
- Whisper 模型路徑：GUI 可設定（預設：`whisper.cpp/models/for-tests-ggml-base.bin`）
- GPU 後端：GUI 可設定（選項：auto, metal, cuda, hip, vulkan, opencl, cpu）
- 執行緒數：預設 `4`（在 ASRRequest 中）
- 輸出格式：GUI 可設定（選項：srt, txt, json, verbose）

### 日誌配置
- Develop mode 日誌觸發條件：
  - `APP_ENV=development`（不分大小寫），或
  - `APP_DEBUG=1`
- 日誌等級：
  - develop mode：`DEBUG`
  - 預設模式：`INFO`
- `TranslationRequest.max_retries` 預設：`1`
- 提示詞檔案：`src/translation/prompts.json`

## 6. 提示詞系統

- 使用 `JsonPromptProvider`
- 讀取 `default_prompt` 與可選 `alt_prompt`
- 若檔案讀取/解析失敗，退回內建預設提示詞
- GUI 可透過 `use_alt_prompt` 切換

## 7. ASR 系統

### whisper.cpp 整合

專案包含完整的 whisper.cpp 整合：

- **whisper.cpp/**：完整的 whisper.cpp 倉庫（226 MB）
  - macOS 預先編譯的 `libwhisper.dylib`
  - 11 個測試模型在 `whisper.cpp/models/`
  - CMake 建置系統供自訂編譯
- **WhisperWrapper**：Python ctypes 綁定
  - 封裝 whisper.cpp C API
  - 自動偵測函式庫路徑
  - 支援所有 whisper.cpp 功能（GPU 加速、多種後端）
- **Transcriber**：高層轉錄器協調
  - 模型載入，失敗時自動 fallback 到 CPU
  - 音訊前置處理與格式轉換
  - 多執行緒轉錄
  - 進度回調

### GPU 加速

支援的後端（依平台自動偵測）：

- **macOS（Apple Silicon）**：`metal`（主要）、`cpu`（後備）
- **Windows**：`cuda`、`hip`、`vulkan`、`cpu`
- **Linux**：`cuda`、`hip`、`vulkan`、`cpu`

GPU 初始化失敗時優雅地 fallback 到 CPU。

### 音訊處理

- **AudioConverter**：轉換音訊為 Whisper 相容格式
  - 要求：16kHz 取樣率、單聲道、PCM float32
  - 使用 `soundfile` 函式庫進行 WAV 轉換
  - 使用 `ffmpeg` 透過 subprocess 處理其他格式
- **AudioDownloader**：從 YouTube 下載音訊
  - 使用 `yt-dlp` 進行影片/音訊提取
  - 支援從瀏覽器讀取 cookies
  - 轉換為 WAV 以供 Whisper 處理

### 輸出格式

- **SRT**：含時間戳的標準字幕格式
- **TXT**：不含時間戳的純文字
- **JSON**：含時間資訊與元資料的結構化輸出
- **Verbose**：含時間範圍的人類可讀格式

## 8. 輸出檔與衝突處理

- `src/utils/file_utils.py` 的 `get_output_path` 決定輸出路徑
- 預設在檔名後加語言後綴（例如 `.zh_tw`、`.en`）
- 取代模式會直接覆寫原始檔
- 舊版 thread 流程中，既有檔案可選覆蓋、重新命名、跳過，逾時預設重新命名
- 備份目錄為來源檔旁 `backup/`

## 9. 錯誤處理與重試

### 翻譯

- HTTP/API 失敗會包裝成 `ExternalServiceError`
- coordinator 只對 `ExternalServiceError` 重試
- 其他例外視為該檔立即失敗
- 執行摘要回報總數、成功數、失敗數

### ASR

- 模型載入失敗會觸發 GPU 到 CPU fallback
- 音訊轉換錯誤會被封裝並回報
- 轉錄錯誤被封裝在 `ExternalServiceError`
- ASRCoordinator 對轉錄失敗進行重試（預設：1 次）
- GPU 後端失敗會自動 fallback 到 CPU

## 10. 測試

目前測試以 application/domain/infrastructure 單元測試為主。

建議（uv）：

```bash
uv run pytest -v
```

相容備援（pip 環境）：

```bash
$env:PYTHONPATH='.'; pytest -v
```

主要覆蓋範圍：

- coordinator 重試策略
- app 事件綁定
- runtime backend priority manifest
- 基礎 infrastructure 適配器
- ASR WhisperWrapper 初始化
- ASR coordinator 工作流程

### ASR 測試腳本

- `test_imports.py`：ASR 模組匯入測試
- `test_gui.py`：GUI 整合測試
- `test_whisper_cpp.py`：whisper.cpp 整合測試

## 11. 封裝說明

目前有封裝樣板：

- `packaging/windows/pyinstaller.spec`
- `packaging/macos/pyinstaller.spec`

參考：[`docs/packaging.md`](./packaging.md)

## 12. 已知限制

- `TranslationCoordinator` 目前將 `file_path` 字串直接傳給 translation client；字幕層級的解析/寫回流程尚未完整整合進 coordinator。
- 舊流程與新流程並存，維護成本較高。
- 部分 UI 文案仍有中英混用，可再統一。
- TypeScript 骨架尚未接入 Python runtime。
- GUI 拖放功能暫時停用（macOS tkinterdnd2 相容性問題）。

## 13. 擴充建議

常見擴充點：

- 新增或替換翻譯後端：
  - 實作與現有 translation client 介面相容的 client
- 增加提示詞版本：
  - 擴充 `prompts.json` 並更新 provider 選擇邏輯
- 新增語言後綴映射：
  - 更新 `src/utils/file_utils.py` 的 `get_language_suffix`
- 強化 coordinator：
  - 將 `TranslationThread` 的字幕流程遷移到 coordinator + repository 抽象

### ASR 擴充

- 新增 Whisper 模型：
  - 將 .bin 檔案放入 `whisper.cpp/models/`
  - 更新 GUI 模型選擇清單
- 新增自訂 GPU 後端：
  - 修改翻譯字典中的 `gpu_backend_options`
  - 更新 WhisperWrapper 以支援新後端
- 整合轉錄→翻譯工作流：
  - 在 ASR 標籤頁新增工作流按鈕，自動將輸出載入翻譯標籤頁
  - 協調 ASR 與 Translation coordinators
- 改善音訊格式支援：
  - 擴充 AudioConverter 以支援更多格式
  - 新增格式特定的前置處理
