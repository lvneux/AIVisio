// 이미지 생성 함수
async function generateImage() {
    // DOM 요소들 가져오기
    const promptInput = document.getElementById('promptInput');
    const generatedImage = document.getElementById('generatedImage');
    const button = document.querySelector('button');

    // 프롬프트가 비어있는지 확인
    if (!promptInput.value.trim()) {
        alert('프롬프트를 입력해주세요.');
        return;
    }

    try {
        // 버튼 비활성화 및 로딩 상태 표시
        button.disabled = true;
        button.textContent = '생성 중...';

        // ComfyUI 워크플로우 설정
        const workflow = {
            "3": {
                "inputs": {
                    "seed": Math.floor(Math.random() * 1000000),  // 랜덤 시드 생성
                    "steps": 20,          // 생성 단계 수
                    "cfg": 7,             // CFG 스케일
                    "sampler_name": "euler",  // 샘플러 이름
                    "scheduler": "normal",     // 스케줄러 타입
                    "denoise": 1,             // 디노이즈 강도
                    "model": ["4", 0],        // 모델 참조
                    "positive": ["6", 0],     // 긍정적 프롬프트
                    "negative": ["7", 0],     // 부정적 프롬프트
                    "latent_image": ["5", 0]  // 잠재 이미지
                },
                "class_type": "KSampler"  // 샘플러 클래스
            },
            "4": {
                "inputs": {
                    "ckpt_name": "allInOnePixelModel_v1.ckpt"  // 체크포인트 모델
                },
                "class_type": "CheckpointLoaderSimple"  // 모델 로더 클래스
            },
            "5": {
                "inputs": {
                    "width": 512,         // 이미지 너비
                    "height": 512,        // 이미지 높이
                    "batch_size": 1       // 배치 크기
                },
                "class_type": "EmptyLatentImage"  // 빈 잠재 이미지 생성 클래스
            },
            "6": {
                "inputs": {
                    "text": promptInput.value + ", pixel",  // 사용자 입력 프롬프트
                    "clip": ["4", 1]           // CLIP 모델 참조
                },
                "class_type": "CLIPTextEncode"  // 텍스트 인코딩 클래스
            },
            "7": {
                "inputs": {
                    "text": "bad quality, blurry, distorted",  // 부정적 프롬프트
                    "clip": ["4", 1]                          // CLIP 모델 참조
                },
                "class_type": "CLIPTextEncode"  // 텍스트 인코딩 클래스
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],  // 샘플 입력
                    "vae": ["4", 2]       // VAE 모델 참조
                },
                "class_type": "VAEDecode"  // VAE 디코딩 클래스
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ComfyUI",  // 파일 이름 접두사
                    "images": ["8", 0]            // 이미지 입력
                },
                "class_type": "SaveImage"  // 이미지 저장 클래스
            }
        };

        // 워크플로우 데이터 출력
        console.log('최종 프롬프트:', workflow['6'].inputs.text);

        // 서버에 이미지 생성 요청
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ workflow })
        });

        // 서버 응답 처리
        const data = await response.json();
        console.log('서버 응답:', data);
        
        // 이미지 표시 처리
        if (data.status === 'completed' && data.image) {

            console.log('이미지 URL:', data.image);
            generatedImage.src = data.image;
            generatedImage.style.display = 'block';  // 이미지 표시
        } else {
            alert('이미지 생성에 실패했습니다.');
            generatedImage.style.display = 'none';   // 이미지 숨김
        }
    } catch (error) {
        // 오류 처리
        console.error('Error:', error);
        alert('오류가 발생했습니다.');
        generatedImage.style.display = 'none';
    } finally {
        // 버튼 상태 복원
        button.disabled = false;
        button.textContent = '이미지 생성';
    }
} 