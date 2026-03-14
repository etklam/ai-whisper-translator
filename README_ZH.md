# AI Whisper Translator（ASR + 翻譯 + 摘要）

桌面 GUI 工具，用於語音轉文字（ASR）、字幕翻譯與逐字稿摘要。以本機優先的流程設計，並支援 OpenAI 相容端點。

本文件為第一次使用者上手指南。維護與架構細節請見技術文件。

## 功能概覽

### 語音轉文字（ASR）
- 支援音訊與影片檔轉錄（SRT/TXT/JSON/Verbose）
- 支援 YouTube 下載
- 支援多種 Whisper 模型（tiny/base/small/medium/large）
- GPU 加速（Metal、CUDA、HIP、Vulkan、OpenCL、CPU）

### 字幕翻譯
- 翻譯 ASR 產出的 SRT
- 兩種引擎：
  - **Ollama / OpenAI 相容端點**（本機或遠端）
  - **LibreTranslate（免費引擎）**（需固定原文語言）
- 批次標記請求，降低往返次數

### 摘要
- 為 ASR 產出摘要（`.summary.txt`）
- 使用同一組 AI 引擎與模型設定

### 設定與提示詞
- GUI 設定儲存在專案根目錄 `.config`
- API Key 不會寫入 `.config`，只保留在環境變數或目前 GUI session
- 翻譯/摘要提示詞可在 GUI 編輯
- 預設值位於 `src/translation/prompts.json`（含多語版本）

## 先決條件

- Python 3.10+

翻譯/摘要（可選）：
- **OpenAI 相容端點**（預設：Ollama `http://localhost:11434/v1/chat/completions`）
  - 環境變數：`OPENAI_COMPAT_ENDPOINT`、`OPENAI_API_KEY`
  - 遠端端點需明確啟用：`ALLOW_REMOTE_AI_ENDPOINTS=1`
- **LibreTranslate**（可選）：`LIBRETRANSLATE_ENDPOINT`、`LIBRETRANSLATE_API_KEY`

ASR：
- 專案已包含 `whisper.cpp/`
- 模型放在 `whisper.cpp/models/`

可選：
- `tkinterdnd2` 拖放功能（已在 `requirements.txt`）

## 安裝（建議 uv）

```bash
uv sync
```

相容備援（pip + requirements.txt）：

```bash
pip install -r requirements.txt
```

## 啟動程式

建議：

```bash
uv run ai-whisper-translator
```

備援：

```bash
python main.py
```

## 第一次設定 AI 引擎

1. 點 **展開 AI 引擎設定**（左側面板切換為 AI 設定）。
2. 設定 **OpenAI 端點** 與（可選）**API Key**。
3. 從下拉選單選擇 **模型**。
4. 視需要調整 **翻譯 / 摘要提示詞**。

注意：
- 預設端點為 Ollama：`http://localhost:11434/v1/chat/completions`
- 若要使用遠端端點，需先設定 `ALLOW_REMOTE_AI_ENDPOINTS=1`
- 模型清單從端點的 `/v1/models` 取得。

## ASR + 翻譯 + 摘要（佇列流程）

1. 加入音訊/影片檔或 YouTube URL 到佇列。
2. 設定 ASR（模型路徑、GPU 後端、語言、輸出格式）。
3. 勾選 **啟用翻譯** 與/或 **啟用摘要**。
4. 按 **開始處理**。

輸出：
- 轉錄：`transcriptions/*.srt`（或指定格式）
- 摘要：`*.summary.txt`（與輸出同路徑）
- 翻譯：以語言後綴輸出（例如 `movie.zh_tw.srt`）

## 翻譯引擎備註

### Ollama / OpenAI 相容
- 使用 `OPENAI_COMPAT_ENDPOINT` + `OPENAI_API_KEY`
- 預設為本機 Ollama
- 本機端點預設允許；遠端端點需明確 opt-in

### LibreTranslate（免費）
- 必須固定原文語言（不可自動偵測）
- 可由 UI 或環境變數設定

## 輸出與備份規則

### 翻譯
- 預設加上語言後綴（例如 `movie.zh_tw.srt`）
- 既有檔案預設由 coordinator 自動重新命名處理
- 啟用 **取代原始檔案** 時，原檔會備份到 `backup/`

## 依賴更新

- 啟動時不會自動安裝或更新套件
- 需要時請手動更新 `yt-dlp`：

```bash
uv pip install --upgrade yt-dlp
```

### ASR
- 輸出到指定資料夾
- SRT 含時間戳
- TXT 純文字
- JSON 含時間與元資料
- Verbose 含段落時間範圍

## 快速排錯

### 模型清單是空的
- 確認端點可連線
- Ollama 請確認 `ollama serve` 與 `ollama list`

### 翻譯一開始就失敗
- 檢查端點與 API Key
- 嘗試小模型或降低並行數

### Whisper 模型找不到
- 確認路徑指向有效 `.bin`
- 模型位於 `whisper.cpp/models/`

### GPU 加速無法運作
- 確認後端支援
- 改用 `auto` 或 `cpu`

## 文件

- 技術文件（英文）：`docs/TECHNICAL.md`
- 技術文件（繁體中文）：`docs/TECHNICAL_ZH.md`
- 打包說明：`docs/packaging.md`

## 授權

MIT License。見 `LICENSE`。
