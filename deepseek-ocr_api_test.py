#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試 DeepSeek-OCR API
直接呼叫 API 並儲存回傳的 markdown 和圖像資料
"""

import requests
import json
import sys
from pathlib import Path


def test_deepseek_ocr(pdf_path: str, output_dir: str = "./test_output"):
    """
    測試 DeepSeek-OCR API

    參數:
        pdf_path: PDF 檔案路徑
        output_dir: 輸出目錄
    """
    # API 設定
    api_url = "http://127.0.0.1:8797/ocr"

    # 確保輸出目錄存在
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"測試檔案: {pdf_path}")
    print(f"API 位址: {api_url}")
    print(f"輸出目錄: {output_dir}")
    print("-" * 60)

    # 讀取 PDF 檔案
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (Path(pdf_path).name, f, 'application/pdf')}

            # API 參數
            data = {
                'enable_description': 'false',  # 是否產生圖片描述
            }

            print("傳送請求到 DeepSeek API...")

            # 傳送請求
            response = requests.post(
                api_url,
                files=files,
                data=data,
                timeout=300
            )

            if response.status_code != 200:
                print(f"API 回傳錯誤: {response.status_code}")
                print(f"錯誤資訊: {response.text[:500]}")
                return False

            # 解析回應
            result = response.json()

            print(f"API 回應成功")
            print(f"回應包含的欄位: {list(result.keys())}")
            print("-" * 60)

            # 提取資料
            markdown_content = result.get("markdown", "")
            page_count = result.get("page_count", 0)
            images_data = result.get("images", {})

            print(f"Markdown 長度: {len(markdown_content)} 字元")
            print(f"頁數: {page_count}")
            print(f"圖像數量: {len(images_data)}")

            if images_data:
                print(f"圖像列表:")
                for img_key in list(images_data.keys())[:10]:
                    img_size = len(images_data[img_key])
                    print(f"   - {img_key}: {img_size} 字元 (base64)")

            print("-" * 60)

            # 儲存 Markdown
            md_file = output_path / f"{Path(pdf_path).stem}_deepseek.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Markdown 已儲存: {md_file}")

            # 儲存完整回應
            json_file = output_path / f"{Path(pdf_path).stem}_response.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                # 為了避免檔案過大，只儲存圖像的部分資訊
                simplified_result = {
                    "markdown": markdown_content,
                    "page_count": page_count,
                    "images_count": len(images_data),
                    "image_keys": list(images_data.keys())
                }
                json.dump(simplified_result, f, ensure_ascii=False, indent=2)
            print(f"回應摘要已儲存: {json_file}")

            # 儲存圖像資料（可選，如果需要）
            if images_data:
                images_file = output_path / f"{Path(pdf_path).stem}_images.json"
                with open(images_file, 'w', encoding='utf-8') as f:
                    json.dump(images_data, f, ensure_ascii=False, indent=2)
                print(f"圖像資料已儲存: {images_file}")

            # 統計資訊
            print("-" * 60)
            print("統計資訊:")

            # 統計表格數量
            import re
            table_count = len(re.findall(r'<table>', markdown_content, re.IGNORECASE))
            print(f"   - HTML 表格: {table_count} 個")

            # 統計圖片引用
            img_ref_count = len(re.findall(r'!\[.*?\]\(.*?\)', markdown_content))
            print(f"   - Markdown 圖片引用: {img_ref_count} 個")

            # 統計行數
            line_count = len(markdown_content.split('\n'))
            print(f"   - Markdown 行數: {line_count} 行")

            print("-" * 60)
            print("測試完成！")

            return True

    except FileNotFoundError:
        print(f"檔案不存在: {pdf_path}")
        return False
    except requests.exceptions.Timeout:
        print(f"請求逾時")
        return False
    except Exception as e:
        print(f"發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函式"""

    success = test_deepseek_ocr(
        pdf_path='cookie.pdf', 
        output_dir='./')


if __name__ == "__main__":
    main()
