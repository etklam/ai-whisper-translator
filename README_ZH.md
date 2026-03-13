# AI Whisper Translator (SRT + ASR) - 快速上手

這是一個以桌面 GUI 操作的 `.srt` 字幕翻譯與語音轉文字工具，使用本機 AI 模型進行翻譯與轉錄。

本文件只聚焦第一次使用者的安裝與上手流程。若你要維護、擴充或理解架構，請改看下方技術文件。

## 這個工具可以做什麼

### 字幕翻譯
- 翻譯單一或多個 SRT 檔案
- 支援拖放匯入（需安裝 `tkinterdnd2`）
- 支援整個資料夾批量匯入與重複檔案過濾
- 支援翻譯前字幕清理
- 目標檔案已存在時可選擇覆蓋、重新命名或跳過

### 語音轉文字（ASR）
- 將音訊檔案轉錄為字幕（wav, mp3, m4a, flac, ogg, wma）
- 從 YouTube 影片下載音訊
- 支援多種 Whisper 模型（tiny, base, small, medium, large）
- GPU 加速（Metal, CUDA, HIP, Vulkan, OpenCL, CPU）
- 多種輸出格式（SRT, TXT, JSON, Verbose）

## 開發進度（截至 2026-03-14）

已完成並可用：
- 透過 Ollama chat completions 進行 SRT 翻譯
- 批次匯入 + 重複檔案過濾 + 拖放匯入（tkinterdnd2）
- 翻譯選項：清理、覆蓋/重新命名/跳過、覆寫備份
- 透過 whisper.cpp 進行 ASR 轉錄（本機模型）
- YouTube 音訊下載（yt-dlp）與音訊轉換流程
- GPU 後端支援並可自動降級到 CPU
- 多種輸出格式（SRT/TXT/JSON/Verbose）
- uv 優先、pip 相容的安裝流程

進行中 / 下一步重點：
- 將舊版字幕翻譯 thread 流程完整併入 coordinator
- UI 文案與語言一致性整理
- macOS/Windows 打包（已存在 PyInstaller 規格）
- 增加 GUI + ASR 邊界案例測試

## 先決條件

- Python 3.10 以上
- 本機 Ollama 服務已啟動（`http://localhost:11434`）- 僅用於翻譯功能
- Ollama 內至少有一個可用模型

可選：
- `tkinterdnd2`（拖放功能；`requirements.txt` 已包含）

ASR 功能已包含：
- `whisper.cpp/` - 完整的 whisper.cpp 函式庫（226 MB）
- macOS 預先編譯的 libwhisper.dylib
- 測試用 Whisper 模型

## 安裝（建議：uv）

```bash
uv sync
```

相容備援（pip + requirements.txt）：

```bash
pip install -r requirements.txt
```

## 啟動 Ollama 並下載模型（僅用於翻譯）

```bash
ollama serve
ollama pull gpt-oss:20b
```

若你已有其他相容於 Ollama chat completions API 的模型，也可以直接使用。

## 啟動程式

建議：

```bash
uv run python main.py
```

相容備援：

```bash
python main.py
```

## Develop Mode 日誌

可用以下任一環境變數開啟大量開發日誌：

```powershell
$env:APP_ENV="development"; uv run python main.py
```

```powershell
$env:APP_DEBUG="1"; uv run python main.py
```

預設模式維持 `INFO` 等級輸出。

## 第一次翻譯（6 步）

1. 切換到 **翻譯** 標籤頁。
2. 點 `選擇 SRT 檔案` 或 `文件夾批量新增` 匯入字幕。
3. 設定 `原文語言` 與 `目標語言`。
4. 從模型下拉選單選擇模型（需要 Ollama 正在執行）。
5. 設定 `並行請求數`（一般建議先從 `3-5` 開始）。
6. 按 `開始翻譯` 開始。

## 第一次語音轉錄（6 步）

1. 切換到 **語音轉文字** 標籤頁。
2. 點 `選擇音訊檔案` 選擇音訊檔案，或輸入 YouTube URL 並點 `從 YouTube 下載`。
3. 選擇 Whisper 模型路徑（預設：`whisper.cpp/models/for-tests-ggml-base.bin`）。
4. 啟用 `使用 GPU 加速` 並選擇 GPU 後端（例如 macOS 使用 `metal`）。
5. 選擇轉錄語言和輸出格式（建議 SRT）。
6. 按 `開始轉錄`。

## 常用選項說明

### 翻譯標籤頁
- `翻譯前自動清理`：移除僅括號內容的字幕行並重排編號。
- `取代原始檔案`：直接覆寫原檔，並先建立備份。
- `翻譯後清理工作區`：完成後自動清空工作區檔案清單。
- `調試模式`：在 console 顯示詳細翻譯過程。

### ASR 標籤頁
- `使用 GPU 加速`：啟用 GPU 加速以加快轉錄速度。
- `GPU 後端`：選擇 GPU 後端（auto, metal, cuda, hip, vulkan, opencl, cpu）。
- `轉錄語言`：選擇語言或自動偵測。
- `輸出格式`：選擇 SRT、TXT、JSON 或 Verbose 格式。

## 輸出與備份規則

### 字幕翻譯
- 預設會在檔名加上語言後綴（例如：`movie.zh_tw.srt`）。
- 若輸出檔已存在，可選 `覆蓋`、`重新命名`、`跳過`。
- 啟用 `取代原始檔案` 時，備份會存到來源檔旁的 `backup/` 資料夾。

### ASR 轉錄
- 輸出檔案會儲存到指定路徑（預設：`transcription.srt`）。
- SRT 格式包含每個字幕段的時間戳。
- TXT 格式包含純文字，無時間戳。
- JSON 格式包含時間資訊與元資料。
- Verbose 格式顯示每個段的開始/結束時間。

## 快速排錯

### 字幕翻譯
- 模型清單是空的：
  - 確認 `ollama serve` 正在執行。
  - 用 `ollama list` 檢查模型是否存在。
- 一開始就翻譯失敗：
  - 檢查是否可連到 `http://localhost:11434`。
  - 嘗試較小的模型或降低並行請求數。

### ASR 轉錄
- Whisper 模型找不到：
  - 確認模型路徑指向有效的 .bin 檔案。
  - 專案已包含測試模型於 `whisper.cpp/models/`。
- GPU 加速無法運作：
  - 確認你的硬體支援選定的後端（例如 Apple Silicon 使用 Metal）。
  - 嘗試設定後端為 `auto` 或 `cpu`。
- 轉錄速度很慢：
  - 使用較小的模型（tiny 或 base）。
  - 啟用 GPU 加速。
  - 增加執行緒數（在 ASR coordinator 程式碼中）。

## 文件

- 完整技術文件（英文）：[`docs/TECHNICAL.md`](docs/TECHNICAL.md)
- 完整技術文件（繁體中文）：[`docs/TECHNICAL_ZH.md`](docs/TECHNICAL_ZH.md)
- 打包說明：[`docs/packaging.md`](docs/packaging.md)

## 授權

MIT License. 見 [`LICENSE`](LICENSE)。
