#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek OCR API Server (vLLM) - 極簡版
返回 Markdown 內容 + 圖像資料
"""
import os
import io
import re
import base64
import argparse
from io import BytesIO
from typing import List, Dict, Tuple

import torch
from PIL import Image, ImageDraw

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from vllm import LLM, SamplingParams
from vllm.model_executor.models.registry import ModelRegistry
from deepseek_ocr import DeepseekOCRForCausalLM
from process.ngram_norepeat import NoRepeatNGramLogitsProcessor
from process.image_process import DeepseekOCRProcessor

# -----------------------
# FastAPI App
# -----------------------
app = FastAPI(title="DeepSeek OCR API (vLLM) - Simple", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# -----------------------
# 全域變數
# -----------------------
llm = None

# 固定 Prompt
PROMPT_OCR = "<image>\n<|grounding|>Convert the document to markdown."
PROMPT_DESC = "<image>\nDescribe this image in detail."

# -----------------------
# 模組級 Monkey Patch
# -----------------------
_original_tokenize = DeepseekOCRProcessor.tokenize_with_images

def _patched_tokenize(self, images, bos=True, eos=True, cropping=True, prompt=None):
    if prompt is not None:
        import config
        old = config.PROMPT
        config.PROMPT = prompt
        try:
            return _original_tokenize(self, images, bos, eos, cropping)
        finally:
            config.PROMPT = old
    return _original_tokenize(self, images, bos, eos, cropping)

DeepseekOCRProcessor.tokenize_with_images = _patched_tokenize

# -----------------------
# 工具函式
# -----------------------
def pdf_to_images(pdf_bytes: bytes, dpi: int = 144) -> List[Image.Image]:
    """PDF 轉圖片"""
    if fitz is None:
        raise RuntimeError("未安裝 PyMuPDF，請執行: pip install PyMuPDF")
    
    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        if img.mode != "RGB":
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
        
        images.append(img)
    
    doc.close()
    return images


def clear_vllm_cache():
    """清理 vLLM 快取"""
    if llm is None:
        return
    try:
        if hasattr(llm.llm_engine, 'input_preprocessor'):
            prep = llm.llm_engine.input_preprocessor
            if hasattr(prep, '_mm_processor_cache'):
                prep._mm_processor_cache.clear()
    except:
        pass


def vllm_generate(image: Image.Image, prompt: str) -> str:
    """vLLM 推理"""
    clear_vllm_cache()
    
    processor = DeepseekOCRProcessor()
    tokenized = processor.tokenize_with_images(images=[image], prompt=prompt)
    
    batch_inputs = [{
        "prompt": prompt,
        "multi_modal_data": {"image": tokenized}
    }]
    
    if prompt == PROMPT_OCR:
        logits_proc = [NoRepeatNGramLogitsProcessor(20, 50, {128821, 128822})]
        params = SamplingParams(
            temperature=0.0,
            max_tokens=4096,
            skip_special_tokens=False,
            logits_processors=logits_proc,
            repetition_penalty=1.05,
        )
    else:
        params = SamplingParams(
            temperature=0.0,
            max_tokens=512,
            skip_special_tokens=False,
        )
    
    outputs = llm.generate(batch_inputs, params)
    return outputs[0].outputs[0].text


def clean_markdown(text: str) -> str:
    """清理 Markdown (移除特殊標記)"""
    # 移除 <|ref|> <|det|> 等標記
    text = re.sub(r'<\|ref\|>.*?<\|/ref\|>', '', text)
    text = re.sub(r'<\|det\|>.*?<\|/det\|>', '', text)
    text = re.sub(r'<\|.*?\|>', '', text)
    text = re.sub(r'\[\[.*?\]\]', '', text)
    
    # 移除長分隔線
    text = re.sub(r'={50,}.*?={50,}', '', text, flags=re.DOTALL)
    
    # 规范化空白
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def extract_images_from_raw(raw_text: str, source_image: Image.Image, page_idx: int) -> Tuple[str, Dict[str, str]]:
    """
    從 DeepSeek OCR 原始輸出中提取圖像並裁切

    參數:
        raw_text: OCR 原始輸出（包含 <|ref|>image<|/ref|><|det|>[[...]]<|/det|> 標記）
        source_image: 原始頁面圖片
        page_idx: 頁面索引

    回傳:
        (處理後的markdown, {image_name: base64_data})
    """
    images_dict = {}
    image_counter = 0

    # 圖像標記模式: <|ref|>image<|/ref|><|det|>[[x0,y0,x1,y1]]<|/det|>
    img_pattern = r'<\|ref\|>image<\|/ref\|><\|det\|>\[\[(.*?)\]\]<\|/det\|>'

    def replace_and_extract(match):
        nonlocal image_counter
        bbox_str = match.group(1)

        try:
            # 解析 bbox: "x0,y0,x1,y1"
            coords = [float(x.strip()) for x in bbox_str.split(',')]
            if len(coords) >= 4:
                x0, y0, x1, y1 = coords[:4]

                # 取得圖片尺寸
                img_width, img_height = source_image.size

                # 轉換座標（DeepSeek 座標是歸一化的 0-1000）
                x0_px = int(x0 * img_width / 1000)
                y0_px = int(y0 * img_height / 1000)
                x1_px = int(x1 * img_width / 1000)
                y1_px = int(y1 * img_height / 1000)

                # 確保座標在範圍內
                x0_px = max(0, min(x0_px, img_width))
                y0_px = max(0, min(y0_px, img_height))
                x1_px = max(0, min(x1_px, img_width))
                y1_px = max(0, min(y1_px, img_height))

                # 裁切圖像
                if x1_px > x0_px and y1_px > y0_px:
                    cropped = source_image.crop((x0_px, y0_px, x1_px, y1_px))

                    # 轉換為 base64
                    buffered = BytesIO()
                    cropped.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

                    # 產生圖像名稱
                    image_name = f"page_{page_idx}_img_{image_counter}.png"
                    images_dict[image_name] = img_base64

                    image_counter += 1

                    # 回傳 markdown 圖片標記
                    return f"![Image {image_counter}]({image_name})"
        except Exception as e:
            print(f"⚠️  圖像提取失敗: {e}")

        return "[圖片]"

    # 替換所有圖像標記
    processed_text = re.sub(img_pattern, replace_and_extract, raw_text)

    return processed_text, images_dict


def generate_image_description(image: Image.Image) -> str:
    """產生圖片描述"""
    try:
        result = vllm_generate(image, PROMPT_DESC)

        # 清理特殊標記
        desc = re.sub(r'<\|ref\|>.*?<\|/ref\|>', '', result)
        desc = re.sub(r'<\|det\|>.*?<\|/det\|>', '', desc)
        desc = re.sub(r'<\|.*?\|>', '', desc)
        desc = re.sub(r'\[\[.*?\]\]', '', desc)
        desc = re.sub(r'\s+', ' ', desc).strip()

        # 截斷到200字元
        if len(desc) > 200:
            cutoff = desc[:200].rfind('.')
            if cutoff > 100:
                desc = desc[:cutoff + 1]
            else:
                desc = desc[:200].rsplit(' ', 1)[0] + '...'
        
        return desc
    except Exception as e:
        print(f"⚠️ 圖片描述失敗: {e}")
        return ""


# -----------------------
# 模型初始化
# -----------------------
def initialize_model(model_path: str, gpu_id: int = 0):
    global llm
    
    ModelRegistry.register_model("DeepseekOCRForCausalLM", DeepseekOCRForCausalLM)
    
    if torch.cuda.is_available():
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    
    os.environ['VLLM_USE_V1'] = '0'
    
    print(f"🔄 載入模型: {model_path}")
    
    llm = LLM(
        model=model_path,
        hf_overrides={"architectures": ["DeepseekOCRForCausalLM"]},
        block_size=256,
        enforce_eager=False,
        trust_remote_code=True,
        max_model_len=8192,
        tensor_parallel_size=1,
        gpu_memory_utilization=0.9,
        max_num_seqs=100,
        disable_mm_preprocessor_cache=True,
    )
    
    print("✅ 模型載入完成")


# -----------------------
# API 路由
# -----------------------
@app.get("/")
async def root():
    return {
        "service": "DeepSeek OCR (vLLM) - Simple",
        "version": "1.0.0",
        "status": "執行中"
    }


@app.get("/health")
async def health():
    return {"status": "健康", "model_ready": llm is not None}


@app.post("/ocr")
async def ocr(
    file: UploadFile = File(...),
    enable_description: bool = Form(False),
):
    """
    OCR 介面 (圖片或 PDF)
    
    參數:
        file: 圖片檔案 (jpg/png) 或 PDF 檔案
        enable_description: 是否產生圖片描述
    
    回傳:
        {
            "markdown": "...",  # Markdown 內容
            "page_count": 1     # 頁數
        }
    """
    if llm is None:
        raise HTTPException(503, "模型未載入")
    
    try:
        contents = await file.read()
        
        # 判斷檔案類型
        if file.filename.lower().endswith('.pdf'):
            images = pdf_to_images(contents)
        else:
            images = [Image.open(BytesIO(contents)).convert("RGB")]
        
        print(f"📄 處理 {len(images)} 頁...")
        
        # 處理每一頁
        md_parts = []
        all_images = {}  # 儲存所有提取的圖像 {image_name: base64_data}

        for idx, img in enumerate(images):
            print(f"   頁 {idx + 1}/{len(images)}")

            # OCR
            raw = vllm_generate(img, PROMPT_OCR)

            # 提取圖像（在清理特殊標記之前）
            processed_text, page_images = extract_images_from_raw(raw, img, idx)
            all_images.update(page_images)

            print(f"      提取了 {len(page_images)} 張圖片")

            # 如果啟用圖片描述,替換圖片標記
            if enable_description:
                # 尋找所有 <|ref|>image<|/ref|> 標記
                img_pattern = r'<\|ref\|>image<\|/ref\|><\|det\|>\[\[.*?\]\]<\|/det\|>'

                def replace_with_desc(match):
                    # 提取 bbox
                    det_match = re.search(r'\[\[(.*?)\]\]', match.group(0))
                    if det_match:
                        # 產生描述
                        desc = generate_image_description(img)
                        return f"[圖片: {desc}]" if desc else "[圖片]"
                    return "[圖片]"

                processed_text = re.sub(img_pattern, replace_with_desc, processed_text)

            # 清理並加入
            cleaned = clean_markdown(processed_text)
            if cleaned:
                md_parts.append(cleaned)

        # 合併所有頁
        final_md = "\n\n---\n\n".join(md_parts)

        print(f"✅ 完成！總共提取 {len(all_images)} 張圖片")

        # 回傳結果（包含圖像資料）
        response_data = {
            "markdown": final_md,
            "page_count": len(images)
        }

        # 如果有圖像，加入回應中
        if all_images:
            response_data["images"] = all_images

        return JSONResponse(response_data)
    
    except Exception as e:
        import traceback
        raise HTTPException(500, f"處理失敗: {e}\n{traceback.format_exc()}")


# -----------------------
# 啟動
# -----------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True, help="模型路徑")
    parser.add_argument("--gpu-id", type=int, default=0, help="GPU ID")
    parser.add_argument("--port", type=int, default=8707, help="埠號")
    parser.add_argument("--host", default="0.0.0.0", help="監聽位址")
    
    args = parser.parse_args()
    
    initialize_model(args.model_path, args.gpu_id)
    
    print(f"\n🚀 服務啟動: http://{args.host}:{args.port}")
    print(f"📖 介面文件: http://{args.host}:{args.port}/docs\n")
    
    uvicorn.run(app, host=args.host, port=args.port, workers=1)


if __name__ == "__main__":
    main()
