import json
from urllib import request
from fastapi import HTTPException
import asyncio

COMFYUI_IP = "127.0.0.1:8188"  # ComfyUI 서버 IP 및 포트

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

async def wait_for_completion(prompt_id, ip):
    while True:
        history = json.loads(request.urlopen(f"http://{ip}/history").read().decode('utf-8'))
        if prompt_id in history:
            if 'outputs' in history[prompt_id]:
                outputs = history[prompt_id]['outputs']
                if '9' in outputs and 'images' in outputs['9']:
                    return outputs['9']['images'][0]['filename']
            break
        await asyncio.sleep(0.1)
    return None 