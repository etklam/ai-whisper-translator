# 代碼審查問題

**日期:** 2026-03-11
**審查者:** Codex (gpt-5.2-codex)
**專案:** ai-whisper-translator

---

## 摘要

本文檔包含對 ai-whisper-translator 專案的全面代碼審查發現，重點關注新的 ASR 整合（whisper.cpp）、GUI 實作、依賴項目和整體可維護性。

**問題總計:**
- 🔴 嚴重: 5
- ⚠️ 重要: 5
- 📝 次要/品質: 4
- 🏗️ 架構: 3

---

## 🔴 嚴重問題（優先級：高）

### 1. 自動語言檢測實際上已停用

**受影響的檔案:**
- `src/gui/app.py`
- `src/application/asr_coordinator.py`
- `src/asr/whisper_wrapper.py`

**問題描述:**
- GUI 將「自動檢測」映射為 `None`
- `ASRCoordinator` 將 `None` 傳遞下去
- `WhisperWrapper.get_full_params()` 只在 `language == "auto"` 時啟用檢測
- **結果:** 「自動檢測」UI 選項完全不檢測語言

**建議修復:**
```python
# 在 ASRCoordinator 或 WhisperWrapper 中
if language is None or language == "auto":
    params.detect_language = True
```

---

### 2. ASR 協調器未關閉 Whisper 上下文（記憶體洩漏風險）

**受影響的檔案:**
- `src/application/asr_coordinator.py`
- `src/asr/whisper_transcriber.py`

**問題描述:**
- `ASRCoordinator.run()` 創建 `Transcriber` 但從未調用 `close()`
- 多次執行會導致上下文累積
- 每個上下文都佔用 GPU 記憶體和模型數據

**建議修復:**
```python
# 選項 1: 使用上下文管理器
def run(self, request: ASRRequest):
    with Transcriber(...) as transcriber:
        result = transcriber.transcribe_file(...)
        return result

# 選項 2: 使用 finally 區塊
def run(self, request: ASRRequest):
    transcriber = Transcriber(...)
    try:
        result = transcriber.transcribe_file(...)
        return result
    finally:
        transcriber.close()
```

---

### 3. GUI 在 YouTube 下載時阻塞

**受影響的檔案:**
- `src/gui/app.py`

**問題描述:**
- `download_from_youtube()` 在 UI 線程同步運行
- `yt-dlp` 呼叫會凍結整個 GUI
- 下載期間沒有進度更新

**建議修復:**
```python
import threading
from queue import Queue

def download_from_youtube(self):
    def download_thread():
        try:
            path = self.downloader.download(url)
            self.after(0, lambda: self._on_download_complete(path))
        except Exception as e:
            self.after(0, lambda: self._on_download_error(e))

    thread = threading.Thread(target=download_thread)
    thread.daemon = True
    thread.start()
```

---

### 4. Whisper.cpp ABI 不匹配風險

**受影響的檔案:**
- `src/asr/whisper_wrapper.py`

**問題描述:**
- ctypes 結構定義長且與 whisper.cpp 標頭檔緊密耦合
- 如果本機 whisper.cpp 版本不同，可能導致執行時崩潰或行為異常
- 沒有版本檢查或相容性防護

**建議修復:**
```python
# 選項 1: 鎖定 whisper.cpp 版本
WHISPER_CPP_VERSION = "1.8.3"
WHISPER_CPP_COMMIT = "abc123def"

# 選項 2: 從標頭檔生成 ctypes
# 使用 ctypesgen 等工具或手動代碼生成

# 選項 3: 添加版本防護
def check_whisper_version():
    actual_version = wrapper.lib.whisper_version_major()
    if actual_version != EXPECTED_VERSION:
        raise RuntimeError(f"Whisper.cpp 版本不匹配: {actual_version} != {EXPECTED_VERSION}")
```

---

### 5. whisper.cpp 目錄未追蹤但未忽略

**受影響的檔案:**
- `.gitignore`
- `whisper.cpp/`

**問題描述:**
- Repo 有未追蹤的 `whisper.cpp/` 目錄
- `.gitignore` 中被註釋掉
- 沒有配置 git submodule
- 風險:
  - 持續顯示為未追蹤
  - 意外提交巨大依賴（226.1 MB）
  - 對新開發者的安裝說明不明確

**建議修復:**
```bash
# 選項 1: 使用 git submodule
git submodule add https://github.com/ggerganov/whisper.cpp.git whisper.cpp
echo "whisper.cpp/" >> .gitignore

# 選項 2: 重新啟用忽略並提供安裝文檔
# 在 .gitignore 中取消註釋:
# whisper.cpp/

# 添加到 README:
# 安裝 whisper.cpp
# git clone https://github.com/ggerganov/whisper.git whisper.cpp
# cd whisper.cpp && make
```

---

## ⚠️ 重要問題（優先級：中）

### 1. UI 語言切換不更新 ASR 標籤頁

**受影響的檔案:**
- `src/gui/app.py`

**問題描述:**
- `update_ui_language()` 只更新翻譯標籤頁控制項
- ASR 標籤和下拉框保持原語言
- 有些標籤是硬編碼的中文

**建議修復:**
```python
def update_ui_language(self, lang_code):
    # 更新現有的翻譯標籤頁
    self._update_translate_tab_lang(lang_code)

    # 添加 ASR 標籤頁更新
    self._update_asr_tab_lang(lang_code)

def _update_asr_tab_lang(self, lang_code):
    translations = {
        'zh-TW': {'asr_tab': '音訊轉錄', ...},
        'en': {'asr_tab': 'Audio Transcription', ...}
    }
    # 將翻譯應用到 ASR 控制項
```

---

### 2. `gpu_backend` 被收集但未使用

**受影響的檔案:**
- `src/application/asr_coordinator.py`
- `src/asr/whisper_transcriber.py`
- `src/asr/whisper_wrapper.py`

**問題描述:**
- `ASRRequest.gpu_backend` 穿過 `ASRCoordinator` 並存儲在 `Transcriber` 中
- 從不影響 whisper.cpp 參數
- 誤導性 UI（用戶認為後端選擇有效）

**建議修復:**
```python
# 選項 1: 實現後端選擇
def get_full_params(self, gpu_backend: str):
    params = self.lib.whisper_full_default_params(WhisperSamplingStrategy.WHISPER_SAMPLING_GREEDY)
    if gpu_backend == "metal":
        params.use_gpu = True
        params.gpu_device = 0  # Metal
    # ... 其他後端
    return params

# 選項 2: 移除設置
# 從 ASRRequest 和 UI 移除 gpu_backend
```

---

### 3. ffmpeg 轉換的臨時檔案從未清理

**受影響的檔案:**
- `src/asr/audio_converter.py`

**問題描述:**
- 當 `_convert_with_ffmpeg()` 寫入臨時檔案時，讀取後不會刪除它
- 可以在系統臨時目錄中累積臨時檔案
- 浪費磁碟空間

**建議修復:**
```python
def _convert_with_ffmpeg(self, input_path: str, output_path: str) -> str:
    temp_file = None
    try:
        if not output_path:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            output_path = temp_file.name
        # ... 轉換邏輯 ...
        return output_path
    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
```

---

### 4. YouTube 輸出檔案名稱清理不匹配

**受影響的檔案:**
- `src/asr/audio_downloader.py`

**問題描述:**
- 你計算 `safe_title` 用於搜索，但沒有告訴 yt-dlp 限制檔案名稱
- 在 Windows/macOS 上，無效字符仍可能產生錯誤
- 清理和 yt-dlp 自己命名之間存在競爭條件

**建議修復:**
```python
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'wav',
        'preferredquality': '192',
    }],
    'restrictfilenames': True,  # 添加這個
    'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
}
```

---

### 5. `.gitignore` 現在忽略 `test_*.py`

**受影響的檔案:**
- `.gitignore`

**問題描述:**
- 將忽略新測試（包括 repo 根目錄的測試）
- 根目錄的 `test_gui.py`、`test_imports.py` 等將被忽略
- 可以隱藏重要的測試檔案

**建議修復:**
```gitignore
# 移除這行:
# test_*.py

# 如果需要，改為忽略特定的測試產物:
# **/test_outputs/
# **/.pytest_cache/
```

---

## 📝 次要/品質注意事項

### 1. `get_logger()` 全局狀態問題

**檔案:** `src/asr/utils/logger.py`

**問題描述:**
- 使用全局 `_logger` 但每次都返回 `logging.getLogger(name)`
- 全局緩存沒有幫助，因為沒有被使用

**建議修復:**
```python
_logger = None

def get_logger(name: str = "asr") -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
    return _logger  # 返回緩存的 logger
```

---

### 2. 未使用的 `check_dependencies()` 函數

**檔案:** `src/asr/audio_converter.py`

**問題描述:**
- `AudioConverter.check_dependencies()` 已定義但從未調用
- 可以提前警告用戶缺少 ffmpeg 或 libsndfile

**建議修復:**
```python
# 在應用初始化中
if not AudioConverter.check_dependencies():
    messagebox.showwarning("依賴缺失",
                        "未安裝 ffmpeg 或 libsndfile。")
```

---

### 3. 低效的音訊樣本複製

**檔案:** `src/asr/whisper_transcriber.py`

**問題描述:**
- 使用 `ctypes.c_float * len(audio_samples)` 複製數據
- 對於大型音訊檔案，這很慢且佔用記憶體

**建議修復:**
```python
# 而不是複製:
samples_ptr = (ctypes.c_float * len(audio_samples))(*audio_samples)

# 使用 numpy 指針:
samples_array = np.ascontiguousarray(audio_samples, dtype=np.float32)
samples_ptr = samples_array.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
```

---

### 4. `select_audio()` 中可能的拼寫錯誤

**檔案:** `src/gui/app.py`

**問題描述:**
- `self.audio_path_label.cget("from")` - "from" 不是 Label 的有效選項
- 可能意圖獲取其他屬性

**建議修復:**
```python
# 驗證你想獲取什麼
# 可能是其中之一:
# self.audio_path_label.cget("text")
# self.audio_path_label.cget("font")
```

---

## 🏗️ 架構/可維護性觀察

### 1. GUI 過於龐大（單體式）

**檔案:** `src/gui/app.py`（440+ 行）

**問題描述:**
- 在一個類中處理翻譯 + ASR + 語言切換 + 對話框 + 菜單邏輯
- 難以測試個別組件
- 難以維護和演進

**建議修復:**
```
src/gui/
├── __init__.py
├── app.py                    # 僅主要協調
├── translate_tab.py          # 翻譯 UI
├── asr_tab.py              # ASR UI
├── dialogs.py              # 訊息對話框
├── language_manager.py     # 本地化
└── widgets.py             # 自定義小部件
```

---

### 2. ASR 協調器設計不一致

**檔案:** `src/application/asr_coordinator.py`

**問題描述:**
- 僅支持單檔案轉錄
- `ASRRequest` 和摘要類型建議未來批次處理
- 尚未使用

**建議修復:**
```python
# 選項 1: 實現批次處理:
@dataclass
class ASRRequest:
    input_paths: List[str]  # 多個檔案
    output_path: str

# 選項 2: 簡化為單檔案:
@dataclass
class ASRRequest:
    input_path: str  # 單個檔案
    output_path: str
```

---

### 3. 錯誤處理不一致

**檔案:** 多個 GUI 檔案

**問題描述:**
- 沒有 ASR 錯誤的一致錯誤表面
- 有些顯示 `messagebox`，有些更新狀態標籤
- 用戶獲得不同的體驗

**建議修復:**
```python
class ASRError(Exception):
    pass

def _handle_asr_error(self, error: Exception):
    logger.error(f"ASR 錯誤: {error}", exc_info=True)
    messagebox.showerror("ASR 錯誤", str(error))
    self.update_status(f"錯誤: {error}")
```

---

## 📦 依賴審查（pyproject.toml）

### 問題:

1. **`tkinterdnd2` 已包含但在代碼中已禁用**
   - 聲明為依賴，但拖放已註釋掉
   - 應該是可選的或移除

2. **系統依賴未記錄**
   - `ffmpeg` - 音訊轉換和 YouTube 下載所需
   - `libsndfile` - `soundfile` 包所需
   - `tk` - Python GUI 庫

3. **沒有明確的 whisper.cpp 依賴**
   - 外部 C 庫，沒有清晰的安裝路徑

### 建議:

```toml
[project]
dependencies = [
  "pysrt>=1.1.2",
  # "tkinterdnd2>=0.3.0",  # 移除或移至可選
  "yt-dlp>=2023.11.16",
  "numpy>=1.24.0",
  "soundfile>=0.12.1",
]

[project.optional-dependencies]
gui-dragdrop = ["tkinterdnd2>=0.3.0"]
```

```markdown
## 系統依賴

### 必需
- Python 3.10+
- tk (Python GUI 庫)
- ffmpeg (音訊轉換，YouTube 下載)
- libsndfile (soundfile 依賴)

### 在 macOS 上安裝
```bash
brew install ffmpeg libsndfile
```

### 在 Ubuntu/Debian 上安裝
```bash
sudo apt-get install ffmpeg libsndfile1
```

### whisper.cpp
詳細說明請參閱 [INSTALL_WHISPER.md](INSTALL_WHISPER.md)。
```

---

## 🎯 建議修復順序（簡短列表）

1. 修復自動語言檢測流程（`None` vs `"auto"`）
2. 確保 `Transcriber` 上下文始終釋放
3. 使 YouTube 下載在 GUI 中非阻塞
4. 添加 ASR UI 本地化更新
5. 澄清 whisper.cpp 依賴管理（submodule 或忽略 + 安裝文檔）
6. 從 `.gitignore` 移除 `test_*.py` 忽略

---

## 📊 摘要統計

| 類別 | 數量 |
|----------|-------|
| 嚴重問題 | 5 |
| 重要問題 | 5 |
| 次要/品質問題 | 4 |
| 架構問題 | 3 |
| 依賴問題 | 3 |
| **總計** | **20** |

---

## 📝 註記

- 未運行測試（未要求）
- 審查重點關注暫存更改和未追蹤檔案
- 所有發現基於靜態代碼分析
- 未執行安全審計

---

**後續步驟:**

1. 決定 whisper.cpp 管理方法
2. 修復嚴重問題（記憶體洩漏、自動檢測、阻塞 UI）
3. 將 GUI 重構為較小的模組以提高可維護性
4. 添加 ASR 工作流程的整合測試
5. 清楚記錄系統依賴

