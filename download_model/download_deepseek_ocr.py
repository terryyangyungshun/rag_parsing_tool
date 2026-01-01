from huggingface_hub import snapshot_download
import sys
try:
    snapshot_download(repo_id="deepseek-ai/DeepSeek-OCR",
                      endpoint="https://hf-mirror.com", # 如果想用鏡像站就留著，不行就刪掉這行
                      )
    print("✅ 模型下載完成")
except Exception as e:
    print(f"⚠️ 模型下載失敗，請檢查網路或 huggingface 登入狀態。錯誤：{e}", file=sys.stderr)
    sys.exit(1)