from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import json
from urllib import request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import asyncio
import io

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

COMFYUI_IP = "127.0.0.1:8188"  # ComfyUI 서버 IP 및 포트

class Workflow(BaseModel):
    workflow: dict

def queue_prompt(prompt_workflow, ip):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    req = request.Request(f"http://{ip}/prompt", data=data)
    try:
        res = request.urlopen(req)
        if res.code != 200:
            raise Exception(f"Error: {res.code} {res.reason}")
        return json.loads(res.read().decode('utf-8'))['prompt_id']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def check_progress(prompt_id: str, ip: str):
    while True:
        try:
            req = request.Request(f"http://{ip}/history/{prompt_id}")
            res = request.urlopen(req)
            if res.code == 200:
                history = json.loads(res.read().decode('utf-8'))
                if prompt_id in history:
                    return history[prompt_id]
        except Exception as e:
            print(f"Error checking progress: {str(e)}")
            await asyncio.sleep(1)  # 1초 대기

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/proxy-image/{filename}")
async def proxy_image(filename: str):
    try:
        # ComfyUI 서버에서 이미지 가져오기
        image_url = f"http://{COMFYUI_IP}/view?filename={filename}"
        response = request.urlopen(image_url)
        image_data = response.read()
        
        # 이미지 타입 확인
        content_type = response.headers.get('content-type', 'image/png')
        
        # 이미지를 스트리밍 응답으로 반환
        return StreamingResponse(io.BytesIO(image_data), media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
async def generate(workflow: Workflow):
    try:
        prompt_id = queue_prompt(workflow.workflow, COMFYUI_IP)
        result = await check_progress(prompt_id, COMFYUI_IP)
        final_image_url = None
        for node_id, node_output in result['outputs'].items():
            if 'images' in node_output:
                for image in node_output['images']:
                    print(f"생성된 이미지 정보: {image}")  # 이미지 정보 로깅
                    # 프록시 URL 사용
                    final_image_url = f"/proxy-image/{image['filename']}"
                    print(f"생성된 이미지 URL: {final_image_url}")  # URL 로깅
        if final_image_url:
            return {"status": "completed", "image": final_image_url}
        else:
            return {"status": "completed", "image": None}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
