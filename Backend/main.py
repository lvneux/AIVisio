from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
from urllib import request
from fastapi.responses import StreamingResponse
import asyncio
import io
from pathlib import Path
from comfyui_utils import *

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
    print("생성 요청")
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
        
        last_node_id = max(result['outputs'].keys(), key=int)  
        last_node_output = result['outputs'][last_node_id]

        if 'images' in last_node_output and last_node_output['images']:
            last_image = last_node_output['images'][-1]  # 가장 마지막 이미지를 선택
            if last_image.get('filename'):  
                final_image_url = f"/proxy-image/{last_image['filename']}"
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