from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="PaddlePaddle/PaddleOCR-VL",
    # endpoint="https://hf-mirror.com", # 如果想用鏡像站就留著，不行就刪掉這行
    # token='<API_TOKEN>', # 如果需要 token 就填，不需要就刪掉這行
    local_dir='./models'
)