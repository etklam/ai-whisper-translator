# AI Whisper Translator (SRT) - 快速上手

這是一個以桌面 GUI 操作的 `.srt` 字幕翻譯工具，使用本機 Ollama 模型進行翻譯。

本文件只聚焦第一次使用者的安裝與上手流程。若你要維護、擴充或理解架構，請改看下方技術文件。

## 這個工具可以做什麼

- 翻譯單一或多個 SRT 檔案
- 支援拖放匯入（需安裝 `tkinterdnd2`）
- 支援整個資料夾批量匯入與重複檔案過濾
- 支援翻譯前字幕清理
- 目標檔案已存在時可選擇覆蓋、重新命名或跳過

## 先決條件

- Python 3.10 以上
- 本機 Ollama 服務已啟動（`http://localhost:11434`）
- Ollama 內至少有一個可用模型

可選：
- `tkinterdnd2`（拖放功能；`requirements.txt` 已包含）

## 安裝（建議：uv）

```bash
uv sync
```

相容備援（pip + requirements.txt）：

```bash
pip install -r requirements.txt
```

## 啟動 Ollama 並下載模型

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

## 第一次翻譯（5 步）

1. 點 `Select SRT Files` 或 `Add Folder` 匯入字幕。
2. 設定 `Source Language` 與 `Target Language`。
3. 從模型下拉選單選擇模型。
4. 設定 `Parallel Requests`（一般建議先從 `3-5` 開始）。
5. 按 `Start Translation` 開始。

## 常用選項說明

- `Auto Clean Before Translation`：移除僅括號內容的字幕行並重排編號。
- `Replace Original File`：直接覆寫原檔，並先建立備份。
- `Clean Workspace After Translation`：完成後自動清空工作區檔案清單。
- `Debug Mode`：在 console 顯示詳細翻譯過程。

## 輸出與備份規則

- 預設會在檔名加上語言後綴（例如：`movie.zh_tw.srt`）。
- 若輸出檔已存在，可選 `Overwrite`、`Rename`、`Skip`。
- 啟用 `Replace Original File` 時，備份會存到來源檔旁的 `backup/` 資料夾。

## 快速排錯

- 模型清單是空的：
  - 確認 `ollama serve` 正在執行。
  - 用 `ollama list` 檢查模型是否存在。
- 一開始就翻譯失敗：
  - 檢查是否可連到 `http://localhost:11434`。
  - 降低並行數或改用較小模型再試。
- 拖放無法使用：
  - 重新同步依賴：`uv sync --reinstall`。
  - 相容備援重裝：`pip install -r requirements.txt`。

## 延伸文件

- 完整技術文件（英文）：[`docs/TECHNICAL.md`](docs/TECHNICAL.md)
- 完整技術文件（繁中）：[`docs/TECHNICAL_ZH.md`](docs/TECHNICAL_ZH.md)
- 封裝說明：[`docs/packaging.md`](docs/packaging.md)

## 授權

MIT License，詳見 [`LICENSE`](LICENSE)。
