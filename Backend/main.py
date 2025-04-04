from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from urllib import request
from fastapi.responses import StreamingResponse
import asyncio
import io
from pathlib import Path

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (프로덕션에서는 특정 도메인만 지정하는 것이 좋습니다)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

COMFYUI_IP = "127.0.0.1:8188"  # ComfyUI 서버 IP 및 포트

def load_workflow(file_path: str) -> dict:
    fp = "./src/" + file_path + ".json"
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="워크플로우 파일을 찾을 수 없습니다")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="유효하지 않은 JSON 형식입니다")
    

def modify_workflow(workflow: dict, prompt: str, negative_prompt: str) -> dict:
    """워크플로우의 프롬프트를 수정합니다."""
    modified_workflow = workflow.copy()
    
    # 프롬프트 수정
    for node_id, node in modified_workflow.items():
        if node.get("class_type") == "CLIPTextEncode":
            if "text" in node["inputs"]:
                if "negative" in node["inputs"].get("text", "").lower():
                    node["inputs"]["text"] = negative_prompt
                else:
                    node["inputs"]["text"] = prompt
    
    return modified_workflow

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

@app.get("/proxy-image/{filename}")
async def proxy_image(filename: str):
    if not filename or filename == "undefined":
        raise HTTPException(status_code=400, detail="유효하지 않은 파일명입니다")
        
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
        print(f"이미지 프록시 에러: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
async def generate(prompt_data: dict):
    try:
        workflowName = prompt_data.get("workflow", "")
        workflow = load_workflow(workflowName)
        
        # 프롬프트 데이터 추출
        prompt = prompt_data.get("prompt", "")
        prompt = prompt + ", pixel"
        negative_prompt = ""

        print(f"받은 프롬프트: {prompt}")
        print(f"받은 데이터: {prompt_data}")

        # 워크플로우 수정
        modified_workflow = modify_workflow(workflow, prompt, negative_prompt)
        print(f"수정된 워크플로우: {json.dumps(modified_workflow, indent=2)}")
        
        # 이미지 생성 요청
        prompt_id = queue_prompt(modified_workflow, COMFYUI_IP)
        print(f"생성된 prompt_id: {prompt_id}")
        
        result = await check_progress(prompt_id, COMFYUI_IP)
        print(f"결과: {json.dumps(result, indent=2)}")
        
        final_image_url = None
        for node_id, node_output in result['outputs'].items():
            if 'images' in node_output and node_output['images']:
                for image in node_output['images']:
                    if image.get('filename'):  # filename이 존재하는 경우만 처리
                        print(f"생성된 이미지 정보: {image}")
                        final_image_url = f"/proxy-image/{image['filename']}"
                        print(f"생성된 이미지 URL: {final_image_url}")

        response_data = {"status": "completed", "image": final_image_url} if final_image_url else {"status": "error", "message": "이미지 생성 실패"}
        print(f"응답 데이터: {json.dumps(response_data, indent=2)}")
        return response_data
    except HTTPException as e:
        print(f"HTTP 에러 발생: {str(e)}")
        raise e
    except Exception as e:
        print(f"일반 에러 발생: {str(e)}")
        import traceback
        print(f"상세 에러: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
