# MinerU 安裝與 API 服務部署指南

本文件提供在 **Ubuntu 24.04** 環境下安裝 MinerU 的完整步驟，並指導如何啟動基於 vLLM 的推理 API 服務。

---

## 📋 系統要求 (Prerequisites)

在開始安裝前，請確保您的環境符合以下建議配置：

- **作業系統**：Ubuntu 24.04 LTS
- **Python 版本**：3.11 或 3.12（強烈建議，不建議使用 3.13）
- **GPU 硬體**：NVIDIA GPU（範例環境為單卡 RTX 4090 24GB）
- **驅動要求**：CUDA Version ≥ 12.1
- **環境管理**：Anaconda / Miniconda

---

## 🛠️ 安裝步驟

### 1. 環境預檢

首先確認系統版本與 GPU 驅動狀態：

```bash
# 查看 Ubuntu 系統版本
cat /etc/os-release

# 確認 CUDA 驅動版本
nvidia-smi

# 確認 Conda 環境
conda --version
```

---

### 2. 建立虛擬環境

使用 Conda 建立一個專屬於 MinerU 的 Python 3.11 環境：

```bash
# 建立環境
conda create --name mineru_2.5 python==3.11 -y

# 啟用環境
conda activate mineru_2.5
```

---

### 3. 下載與解壓縮源碼

從官方 GitHub 下載指定版本的 Release 壓縮檔：

```bash
# 下載 MinerU v2.6.4
wget https://github.com/opendatalab/MinerU/archive/refs/tags/mineru-2.6.4-released.tar.gz

# 解壓縮
tar -xzvf mineru-2.6.4-released.tar.gz

# 進入專案目錄
cd MinerU-mineru-2.6.4-released
```

---

### 4. 安裝專案相依套件

執行以下指令安裝 MinerU 及其所有必要的相依函式庫：

```bash
pip install -e .[all]
```

安裝完成後，可透過 `pip show mineru` 確認安裝狀態。

---

### 5. 下載預訓練模型

MinerU 提供了自動化腳本下載所有必要的模型權重。您可以根據網路環境選擇來源（modelscope 或 huggingface）。

```bash
# 執行自動下載腳本
mineru-models-download
```

- `pipeline`：下載文件解析（Layout/OCR）核心模型
- `vlm`：下載視覺語言模型（MinerU2.0-2505-0.9B）
- `all`：下載上述所有內容

> 註：下載的模型預設儲存於 `~/.cache/huggingface/hub`，且腳本會自動在 `~/mineru.json` 生成對應的路徑配置。

---

## 🌐 啟動 vLLM API 服務

MinerU 支援啟動 API 服務，讓您可以透過 HTTP 請求進行文件解析。

### 1. 啟動服務器

在啟動前，請務必將模型來源指向本地路徑：

```bash
# 設定環境變數
export MINERU_MODEL_SOURCE=local

# 啟動 API 服務（指定連接埠 50000）
mineru-api --port 50000
```

---

### 2. 存取 API 文件

服務啟動後，您可以開啟瀏覽器訪問以下位址，查看 Swagger UI 互動式文件：

[http://localhost:50000/docs](http://localhost:50000/docs)