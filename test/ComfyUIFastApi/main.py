from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from urllib import request
import io
from utils.comfy_utils import queue_prompt, wait_for_completion, COMFYUI_IP

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class PromptRequest(BaseModel):
    prompt: str

def create_workflow(prompt: str):
    return {
        "3": {
            "inputs": {
                "seed": 123456,
                "steps": 20,
                "cfg": 7,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": "allInOnePixelModel_v1.ckpt"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": 512,
                "height": 512,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": prompt + ", pixel",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": "bad quality, blurry, distorted",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }

@app.post("/generate")
async def generate_image(request: PromptRequest):
    try:
        workflow = create_workflow(request.prompt)
        prompt_id = queue_prompt(workflow, COMFYUI_IP)
        filename = await wait_for_completion(prompt_id, COMFYUI_IP)
        
        if filename:
            return {"filename": filename}
        else:
            raise HTTPException(status_code=500, detail="이미지 생성에 실패했습니다")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/proxy-image/{filename}")
async def proxy_image(filename: str):
    try:
        image_url = f"http://{COMFYUI_IP}/view?filename={filename}"
        response = request.urlopen(image_url)
        image_data = response.read()
        content_type = response.headers.get('content-type', 'image/png')
        return StreamingResponse(io.BytesIO(image_data), media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 