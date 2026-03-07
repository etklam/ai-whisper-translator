# 技術文件（繁體中文）

本文件給維護者與開發者使用。

## 1. 範圍與現況

- 目前正式執行路徑是 Python 應用。
- 主入口為 [`main.py`](../main.py)，再呼叫 [`src/main.py`](../src/main.py)。
- GUI 主要在 [`src/gui/app.py`](../src/gui/app.py)。
- 專案已具備 application/domain/infrastructure 分層，但仍在整合期。
- `src/*.ts` 的 TypeScript 檔目前為草稿骨架，未接入現行執行流程。

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

- `src/application/`
  - `models.py`：請求模型（`TranslationRequest`）
  - `events.py`：進度事件（`ProgressEvent`）
  - `translation_coordinator.py`：流程協調、重試與彙總
- `src/domain/`
  - 服務介面與領域錯誤定義
- `src/infrastructure/`
  - `translation/ollama_translation_client.py`：呼叫 Ollama `/v1/chat/completions`
  - `prompt/json_prompt_provider.py`：讀取 JSON 提示詞
  - `subtitles/pysrt_subtitle_repository.py`：字幕檔操作適配層
- `src/gui/`
  - Tkinter 介面、檔案匯入、事件綁定、進度呈現
- `src/translation/`
  - 舊版 thread 字幕翻譯流程（`TranslationThread`）
- `src/utils/`
  - 輸出命名、備份建立、字幕清理工具

## 4. 端到端流程

### 預設流程（GUI + Coordinator）

1. 使用者在 UI 匯入檔案。
2. 設定來源語言、目標語言、模型、並行數。
3. 觸發翻譯。
4. 產生 `TranslationRequest` 並交給 coordinator。
5. coordinator 對 `ExternalServiceError` 進行重試（最多 `max_retries`）。
6. coordinator 發送 `ProgressEvent`。
7. GUI 更新進度條與完成狀態。

### 舊版 Thread 流程

`TranslationThread` 仍保留「分批翻譯字幕、檔名衝突處理、輸出存檔」的完整邏輯，目前與新版流程並存。

## 5. 設定與預設值

- Ollama 端點（預設）：`http://localhost:11434/v1/chat/completions`
- 主程序環境變數：`main.py` 內設定 `OLLAMA_NUM_PARALLEL=5`
- UI 預設並行數：`10`
- `TranslationRequest.max_retries` 預設：`1`
- 提示詞檔案：`src/translation/prompts.json`

## 6. 提示詞系統

- 使用 `JsonPromptProvider`
- 讀取 `default_prompt` 與可選 `alt_prompt`
- 若檔案讀取/解析失敗，退回內建預設提示詞
- GUI 可透過 `use_alt_prompt` 切換

## 7. 輸出檔與衝突處理

- `src/utils/file_utils.py` 的 `get_output_path` 決定輸出路徑
- 預設在檔名後加語言後綴（例如 `.zh_tw`、`.en`）
- 取代模式會直接覆寫原始檔
- 舊版 thread 流程中，既有檔案可選覆蓋、重新命名、跳過，逾時預設重新命名
- 備份目錄為來源檔旁 `backup/`

## 8. 錯誤處理與重試

- HTTP/API 失敗會包裝成 `ExternalServiceError`
- coordinator 只對 `ExternalServiceError` 重試
- 其他例外視為該檔立即失敗
- 執行摘要回報總數、成功數、失敗數

## 9. 測試

目前測試以 application/domain/infrastructure 單元測試為主。

執行全部測試：

```bash
$env:PYTHONPATH='.'; pytest -v
```

主要覆蓋範圍：

- coordinator 重試策略
- app 事件綁定
- runtime backend priority manifest
- 基礎 infrastructure 適配器

## 10. 封裝說明

目前有封裝樣板：

- `packaging/windows/pyinstaller.spec`
- `packaging/macos/pyinstaller.spec`

參考：[`docs/packaging.md`](./packaging.md)

## 11. 已知限制

- `TranslationCoordinator` 目前將 `file_path` 字串直接傳給 translation client；字幕層級的解析/寫回流程尚未完整整合進 coordinator。
- 舊流程與新流程並存，維護成本較高。
- 部分 UI 文案仍有中英混用，可再統一。
- TypeScript 骨架尚未接入 Python runtime。

## 12. 擴充建議

常見擴充點：

- 新增或替換翻譯後端：
  - 實作與現有 translation client 介面相容的 client
- 增加提示詞版本：
  - 擴充 `prompts.json` 並更新 provider 選擇邏輯
- 新增語言後綴映射：
  - 更新 `src/utils/file_utils.py` 的 `get_language_suffix`
- 強化 coordinator：
  - 將 `TranslationThread` 的字幕流程遷移到 coordinator + repository 抽象
