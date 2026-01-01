#!/usr/bin/env python3
"""
測試 MinerU API 的不同 backend
透過 50000 埠口呼叫，傳遞不同的 backend 參數來使用不同的模型
"""

import requests
import sys
from pathlib import Path

def test_mineru_api(pdf_path: str, backend: str = "pipeline"):
    """
    測試 MinerU API

    參數:
        pdf_path: PDF 檔案路徑
        backend: 後端類型，可選值：
                - "pipeline"（預設，使用本地 PyTorch）
                - "vlm-vllm-async-engine"（使用 vLLM 加速）
    """
    api_url = "http://localhost:50000/file_parse"

    print(f"\n{'='*60}")
    print(f"測試 MinerU API，backend: {backend}")
    print(f"{'='*60}")
    print(f"API URL: {api_url}")
    print(f"PDF 檔案: {pdf_path}")
    print(f"Backend: {backend}")
    print()

    # 檢查檔案是否存在
    if not Path(pdf_path).exists():
        print(f"錯誤: 檔案不存在 - {pdf_path}")
        return None

    try:
        # 開啟檔案並發送請求
        with open(pdf_path, 'rb') as f:
            files = [('files', (Path(pdf_path).name, f, 'application/pdf'))]
            data = {
                'backend': backend,
                'parse_method': 'auto',
                'lang_list': 'ch', # 預設簡體中文, chinese_cht 繁體中文, en 英文
                'return_md': 'true',
                'return_middle_json': 'false',
                'return_model_output': 'false',
                'return_content_list': 'false',
                'start_page_id': '0',
                'end_page_id': '1',  # 只處理前2頁，快速測試
            }

            print("發送請求中...")
            response = requests.post(
                api_url,
                files=files,
                data=data,
                timeout=300
            )

        # 檢查回應
        if response.status_code != 200:
            print(f"請求失敗: HTTP {response.status_code}")
            print(f"回應: {response.text[:500]}")
            return None

        # 解析 JSON 回應
        result = response.json()

        # 提取資訊
        backend_used = result.get('backend', 'unknown')
        version = result.get('version', 'unknown')
        results = result.get('results', {})

        print(f"請求成功！")
        print(f"   使用的 backend: {backend_used}")
        print(f"   版本: {version}")
        print(f"   結果數量: {len(results)}")

        # 提取 markdown 內容
        if results:
            file_key = list(results.keys())[0]
            md_content = results[file_key].get('md_content', '')

            print(f"\nMarkdown 內容預覽（前500字元）:")
            print("-" * 60)
            print(md_content[:500])
            print("-" * 60)

            # 儲存 markdown 到檔案
            output_file = f"output_{backend}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            print(f"\n完整 Markdown 已儲存到: {output_file}")

            return md_content
        else:
            print("未找到結果")
            return None

    except Exception as e:
        print(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return None
    
def main():
    # 預設測試檔案
    pdf_path = "cookie.pdf"

    print(f"\n開始測試 MinerU API 的不同 backend")
    print(f"測試檔案: {pdf_path}\n")

    # 測試 1: pipeline backend（本地 PyTorch）
    print("\n" + "="*60)
    print("測試 1: pipeline backend（本地 PyTorch）")
    print("="*60)
    result_pipeline = test_mineru_api(pdf_path, backend="pipeline")

    # 測試 2: vLLM backend（vLLM 加速）
    print("\n" + "="*60)
    print("測試 2: vlm-vllm-async-engine backend（vLLM 加速）")
    print("="*60)
    result_vllm = test_mineru_api(pdf_path, backend="vlm-vllm-async-engine")

    # 總結
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    print(f"Pipeline backend: {'成功' if result_pipeline else '失敗'}")
    print(f"vLLM backend: {'成功' if result_vllm else '失敗'}")

    if result_pipeline and result_vllm:
        print("\n所有測試通過！MinerU 可以透過 backend 參數切換不同模型")

    print("\n💡 提示：")
    print("  - pipeline：使用本地 PyTorch，適合除錯")
    print("  - vlm-vllm-async-engine：使用 vLLM 加速，速度更快")


if __name__ == "__main__":
    main()