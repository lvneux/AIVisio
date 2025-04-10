import json
from urllib import request
from fastapi import HTTPException
import asyncio
import random

def load_workflow(file_path: str) -> dict:
    """워크플로우 파일 로드"""
    fp = "./src/" + file_path + ".json"
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="워크플로우 파일을 찾을 수 없습니다")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="유효하지 않은 JSON 형식입니다")

def modify_workflow(workflowName: str, workflow: dict, positive_prompt: str, negative_prompt: str) -> dict:
    """워크플로우의 프롬프트를 수정"""
    modified_workflow = workflow.copy()

    if workflowName == "allInOnePixelModel_v1":
        return modify_allInOnePixelModel_v1(modified_workflow, positive_prompt, negative_prompt)
    elif workflowName == "LM_model":
        return modify_LM_model(modified_workflow, positive_prompt, negative_prompt)


def modify_LM_model(modified_workflow:dict, positive_prompt: str, negative_prompt: str) -> dict:
    for node_id, node in modified_workflow.items():
        if node.get("class_type") == "Searge_LLM_Node":
            node['inputs']["random_seed"] = random.randint(0, 1000000)

            if "positive" in node["_meta"].get("title", "").lower():
                node["inputs"]["text"] = positive_prompt
            elif "negative" in node["_meta"].get("title", "").lower():
                node["inputs"]["text"] = negative_prompt

    return modified_workflow

def modify_allInOnePixelModel_v1(modified_workflow:dict, positive_prompt: str, negative_prompt:str) -> dict:
    # 프롬프트 수정
    for node_id, node in modified_workflow.items():
        if node.get("class_type") == "KSampler":
            node['inputs']["seed"] = random.randint(0, 1000000)

        if node.get("class_type") == "CLIPTextEncode":
            if "text" in node["inputs"]:
                if "positive" in node["_meta"].get("title", "").lower():
                    node["inputs"]["text"] = positive_prompt
                elif "negative" in node["_meta"].get("title", "").lower():
                    node["inputs"]["text"] = negative_prompt
    
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
    """프롬프트 진행 상태 확인"""
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
