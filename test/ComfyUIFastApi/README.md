# LLM이용하여 간단하게 만든 이미지 생성 페이지 프로토타입.

사용한 체크포인트 모델
https://civitai.com/models/34/all-in-one-pixel-model

## 사용 법
1. comfyUI 서버 실행
2. FastAPI 서버 실행 (명령어 : uvicorn main:app --reload) (필요한 라이브러리들 install 필요. 추후 가상환경 구현 버전 만들어서 한번에 받을 수 있도록 수정 예정)
3. http://127.0.0.1:8000/ 로 접속
4. 프롬프트 입력 후 버튼 클릭

## 추가 해야 할 사항
1. comfyUI background실행.
2. 가상환경 구현.
3. 프로젝트 디렉토리 구조 수정.
4. workflow api json파일을 직접 읽어와서 수정.
5. 기타등등
