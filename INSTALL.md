# 📖 多模型文件解析工具安裝手冊 (MinerU、PaddleOCR-VL、DeepSeek-OCR)

本文件會帶你在 **Ubuntu 24.04** 環境下完成 `MinerU`、`PaddleOCR-VL` 以及 `DeepSeek-OCR` 的部署。這三套工具分別代表目前主流的 PDF 結構化解析與視覺語言模型 OCR 技術。

---

## 🛠️ 第一部分：[MinerU 安裝指南](./MinerU_INSTALL_README.md)

MinerU 是一款功能強大的智慧文件解析工具，支援將 PDF 轉換成包含公式、表格的 Markdown 格式。

### 📋 系統需求

請先確認你的環境符合下列建議：

- **作業系統**：Ubuntu 24.04 LTS
- **Python 版本**：3.11 或 3.12 (強烈建議，3.13 不建議)
- **GPU**：NVIDIA GPU (範例：單卡 RTX 4090 24GB)
- **驅動**：CUDA 版本 ≥ 12.1
- **環境管理**：Anaconda / Miniconda

---

### 🛠️ 安裝步驟

#### 1. 環境預檢

先確認系統版本與 GPU 驅動狀態：

```bash
cat /etc/os-release         # 查看 Ubuntu 系統版本
nvidia-smi                  # 確認 CUDA 驅動版本
conda --version             # 確認 Conda 是否可用
```

---

#### 2. 建立虛擬環境

用 Conda 建立專屬 MinerU 的 Python 3.11 環境：

```bash
conda create --name mineru_2.5 python=3.11 -y
conda activate mineru_2.5
```

---

#### 3. 下載與解壓縮原始碼

從 GitHub 下載指定版本 Release 壓縮檔：

```bash
wget https://github.com/opendatalab/MinerU/archive/refs/tags/mineru-2.6.4-released.tar.gz
tar -xzvf mineru-2.6.4-released.tar.gz
cd MinerU-mineru-2.6.4-released
```

---

#### 4. 安裝相依套件

安裝 MinerU 及所有必要相依函式庫：

```bash
pip install -e .[all]
```

安裝完成後，可用 `pip show mineru` 確認狀態。

---

#### 5. 下載預訓練模型

MinerU 提供自動化腳本下載所有必要模型權重。可依網路環境選擇來源 (modelscope 或 huggingface)。

```bash
mineru-models-download
```

- `pipeline`：下載文件解析 (Layout/OCR) 核心模型
- `vlm`：下載視覺語言模型 (MinerU2.0-2505-0.9B)
- `all`：下載上述所有內容

> 註：模型預設儲存於 `~/.cache/huggingface/hub`，腳本會自動在 `~/mineru.json` 生成對應路徑設定。

---

### 🌐 啟動 vLLM API 服務

MinerU 支援 API 服務，可用 HTTP 請求進行文件解析。

#### 1. 啟動服務

啟動前，請將模型來源指向本地路徑：

```bash
export MINERU_MODEL_SOURCE=local
mineru-api --port 50000
```

---

#### 2. 存取 API 文件

服務啟動後，可用瀏覽器開啟：

<http://localhost:50000/docs>

---

## 🧪 連接測試

執行測試腳本驗證服務：

```bash
python ./api_test/mineru_api_test.py
```

> 詳細安裝與操作流程請參考：[MinerU 安裝說明文件](./MinerU_INSTALL_README.md)

---

## 🛠️ 第二部分：[PaddleOCR-VL 安裝指南](./PaddleOCR-VL_INSTALL_README.md)

PaddleOCR-VL 結合 PP-DocLayoutV2 與 0.9B 視覺語言模型，提供高精度的文件感知識別。

### 1. 建立獨立環境

為避免與 MinerU 相依套件衝突，請務必建立獨立環境：

```bash
conda create -n ppocr-vllm python=3.11 -y
conda activate ppocr-vllm
```

---

### 2. 安裝 PaddlePaddle 與核心組件

針對 CUDA 12.x 環境安裝 Paddle 3.2.0：

```bash
python -m pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
python -c "import paddle; paddle.utils.run_check()"
python -m pip install https://paddle-whl.bj.bcebos.com/nightly/cu126/safetensors/safetensors-0.6.2.dev0-cp38-abi3-linux_x86_64.whl
```

---

### 3. 下載模型與 Flash-Attention 加速

```bash
# 安裝 huggingface_hub 並下載模型(會產生 models/ 資料夾)
pip install huggingface_hub
python download_paddleocr_vl.py

# 安裝 OCR 套件與 Flash-Attention 2.8.2
pip install paddleocr[all]
pip install https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.2/flash_attn-2.8.2+cu12torch2.4cxx11abiFALSE-cp311-cp311-linux_x86_64.whl --no-build-isolation

# 安裝 vLLM 服務相依套件
paddleocr install_genai_server_deps vllm

# 降級 flash-attn 至 v2.7.3 以確保 vLLM 推論穩定
pip install https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.3/flash_attn-2.7.3+cu12torch2.8cxx11abiFALSE-cp311-cp311-linux_x86_64.whl
```

---

### 4. 啟動 PaddleOCR-VL 雙層服務

需開兩個終端機視窗：

#### 視窗 A：啟動 vLLM 後端推論引擎

```bash
paddlex_genai_server --model_name PaddleOCR-VL-0.9B --backend vllm --host 0.0.0.0 --port 8118
```

#### 視窗 B：配置並啟動 PaddleX 前端服務

```bash
# 初始化並取得設定檔
paddlex --install serving
paddlex --get_pipeline_config PaddleOCR-VL
```

手動編輯 `PaddleOCR-VL.yaml`，將 `backend` 改為 `vllm-server`，`server_url` 改為 `http://localhost:8118/v1`。

```yaml
genai_config:
    backend: vllm-server
    server_url: http://localhost:8118/v1

```

啟動 API 服務：

```bash
paddlex --serve --pipeline PaddleOCR-VL.yaml --port 10800 --paddle_model_dir ./models
```

## 🧪 連接測試

執行測試腳本驗證服務：

```bash
python ./api_test/paddleocr_api_test.py
```

> 詳細安裝與操作流程請參考：[PaddleOCR-VL 安裝說明文件](./PaddleOCR-VL_INSTALL_README.md)

---

## 🛠️ 第三部分：[DeepSeek-OCR 安裝指南](./Deepseek-ocr_README.md)

DeepSeek-OCR 提供高效能的 OCR 與多模態文件解析能力，支援 vLLM 推論加速，適合大規模文件處理需求。

### 1. 建立 Python 虛擬環境

請先建立獨立的 Python 虛擬環境，避免與其他專案相依套件衝突：

```bash
conda create -n deepseek-ocr python=3.12.9 -y
conda activate deepseek-ocr
```

---

### 2. 下載模型

安裝 huggingface\_hub 套件並下載 DeepSeek-OCR 模型：

```bash
pip install huggingface_hub
python download_deepseek_ocr.py
```

---

### 3. 安裝相關相依套件

安裝 torch、vllm、requirements.txt 及 flash-attention：

```bash
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu118
pip install https://github.com/vllm-project/vllm/releases/download/v0.8.5/vllm-0.8.5+cu118-cp38-abi3-manylinux1_x86_64.whl
pip install -r DeepSeek-OCR-vllm/requirements.txt
pip install flash-attn==2.7.3 --no-build-isolation
```

---

### 4. 啟動 DeepSeek OCR API 服務

使用我們提供的 `ocr_client.py` 啟動 API 服務：

```bash
python ~/rag_parsing_tool/DeepSeek-OCR-vllm/ocr_client.py --model-path deepseek-ai/DeepSeek-OCR --port 8797
```

啟動成功後，可用瀏覽器開啟 <http://127.0.0.1:8797/docs> 查看 API 文件。

---

## 🧪 連接測試

執行測試腳本驗證服務：

```bash
python ./api_test/deepseek_ocr_api_test.py
```

---

> 詳細安裝與操作流程請參考：[DeepSeek-OCR 安裝說明文件](./Deepseek-ocr_README.md)

---
