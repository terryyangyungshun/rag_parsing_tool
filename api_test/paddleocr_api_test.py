import base64
import json
import requests
import os

# === 1. 服務端位址 ===
SERVER_URL = "http://localhost:10800/layout-parsing"

# === 2. 待處理檔案路徑 ===
input_path = "cookie.pdf"   # 也可以是 test.png
output_md = "result1.md"

# === 3. 讀取檔案並轉為 Base64 ===
with open(input_path, "rb") as f:
    file_base64 = base64.b64encode(f.read()).decode("utf-8")

# === 4. 組成 JSON 請求內容 ===
payload = {
    "file": file_base64,
    "fileType": 0 if input_path.lower().endswith(".pdf") else 1,
    "prettifyMarkdown": True,
    "visualize": False,
}

headers = {"Content-Type": "application/json"}

# === 5. 發送請求 ===
resp = requests.post(SERVER_URL, headers=headers, data=json.dumps(payload))

# === 6. 解析回應 ===
if resp.status_code == 200:
    data = resp.json()
    if data.get("errorCode") == 0:
        # PDF 的結果在 layoutParsingResults 陣列中
        results = data["result"]["layoutParsingResults"]
        md_text = ""
        for i, page in enumerate(results, 1):
            md_text += f"\n\n# 第 {i} 頁\n\n"
            md_text += page["markdown"]["text"]

        with open(output_md, "w", encoding="utf-8") as f:
            f.write(md_text)
        print(f"成功產生 Markdown：{output_md}")
    else:
        print(f"服務端錯誤：{data.get('errorMsg')}")
else:
    print(f"HTTP 錯誤：{resp.status_code}")
    print(resp.text)
