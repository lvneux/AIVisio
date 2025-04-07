<template>
  <div class="container">
    <!-- 좌측 영역 -->
    <div class="left-panel">
      <!-- 로고 -->
      <img src="@/assets/aivisio_logo.png" alt="AIVISIO Logo" class="logo" />

      <!-- Prompt 입력 -->
      <div class="prompt-box">
        <label for="prompt" class="prompt-label">prompt</label>
        <textarea
          id="prompt"
          v-model="prompt"
          placeholder="이미지 설명을 입력하세요"
        ></textarea>

        <!-- 이미지 생성 버튼 -->
        <img
          src="@/assets/btn_create_image.png"
          alt="Create Image"
          class="create-btn"
          @click="generateImage"
        />
      </div>

      <!-- 모델 선택 -->
      <div>선택 모델: {{ selected }}</div>
      <select v-model="selected">
        <option disabled value="">다음 중 하나를 선택하세요</option>
        <option>allInOnePixelModel_v1</option>
        <option>dreamshaper_8</option>
        <option>모델 3</option>
      </select>

      <!-- ✅ 썸네일 리스트 -->
      <div class="thumbnail-grid">
        <div
          v-for="(img, index) in images"
          :key="index"
          class="thumbnail"
          @click="selectImage(img)"
         :class="{ selected: img === selectedImage }"
        >
          <img :src="img" alt="AI 이미지 썸네일" />
        </div>
      </div>
    </div>
    
    
    <!-- 중앙 미리보기 -->
     <!--
    <div class="image-viewer">
      <img v-if="selectedImage" :src="selectedImage" alt="선택된 이미지" />
    </div>
    -->

    <!-- 가운데 이미지 출력 영역 -->
    <div class="image-viewer">
      <img v-if="imageUrl" :src="imageUrl" alt="Generated" />
    </div>

    <!-- 우측 편집기 -->
    <div class="editor-placeholder">
      편집기능 추가 예정
    </div>
  </div>
</template>


<script lang="ts">
import { defineComponent, ref } from 'vue'

export default defineComponent({
  name: 'App',
  setup() {
    const prompt = ref('')
    //const imageUrl = ref('')
    const selected = ref('')
    const selectedImage = ref('') // ✅ 선택된 썸네일 이미지
    const images = ref<string[]>([]) // ✅ 썸네일 목록
    const imageUrl = ref('')
    const errorMsg = ref('')

    // ✅ 더미 이미지 배열 (public/assets/ 에 저장해두기)
    const dummyImages = [
      '/assets/dummy1.jpg',
      '/assets/dummy2.jpg',
      '/assets/dummy3.jpg',
    ]

    const generateImage = async () => {
      console.log("버튼 클릭됨1")
      if (!prompt.value.trim()) return // 프롬프트가 비어 있으면 요청하지 않음
      console.log("버튼 클릭됨2")

      try {
        const response = await fetch('http://localhost:8000/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            prompt: prompt.value,
            workflow: selected.value
          }),
        })

        const data = await response.json()
        console.log('서버 응답:', data) // 서버 응답 확인

        if (data.status === 'completed' && data.image) {
          // 이미지 URL이 있는 경우 처리
          imageUrl.value = `http://127.0.0.1:8000${data.image}`
          errorMsg.value = '' // 에러 메시지 초기화
        } else {
          // 에러 처리
          console.error(data.message || '이미지 생성 실패')
          errorMsg.value = data.message || '이미지 생성에 실패했습니다.'
        }
      } catch (error) {
        console.error('요청 실패:', error)
        errorMsg.value = '이미지 생성 중 오류가 발생했습니다.'
      }
    }

    const generateImages = () => {
      if (!prompt.value.trim()) return
      images.value = dummyImages // 나중에 서버 응답으로 대체
      selectedImage.value = ''   // 선택 초기화
    }

    const selectImage = (img: string) => {
      selectedImage.value = img
    }

    return {
      prompt,
      selected,
      selectedImage,
      images,
      imageUrl,
      errorMsg,
      generateImages,
      generateImage,
      selectImage,
    }
  },
})
</script>


<style scoped>
/* 전체 레이아웃 */
.container {
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 100vw;
  font-family: 'Segoe UI', sans-serif;
}

/* 좌측 영역 */
.left-panel {
  width: 20%;
  padding: 20px;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

/* 로고 이미지 */
.logo {
  width: 120px;
}

/* Prompt 입력 박스 */
.prompt-box {
  width: 100%;
  background-color: #f8f8f8;
  padding: 15px;
  border-radius: 10px;
  text-align: left;
}

.prompt-label {
  display: block;
  font-weight: bold;
  margin-bottom: 8px;
}

.prompt-box textarea {
  width: 100%;
  height: 100px;
  resize: none;
  padding: 8px;
  font-size: 14px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

/* 이미지로 된 버튼 */
.create-btn {
  margin-top: 12px;
  width: 140px;
  cursor: pointer;
}

/* 셀렉트 버튼 */
select {
  width: 100%;
  padding: 8px;
  margin-top: 10px;
  border-radius: 5px;
  border: 1px solid #ccc;
  font-size: 14px;
}

/* 썸네일 그리드 */
.thumbnail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  width: 100%;
  margin-top: 20px;
}

.thumbnail img {
  width: 100%;
  height: auto;
  cursor: pointer;
  border-radius: 5px;
  border: 2px solid transparent;
  transition: border 0.2s ease;
}

.thumbnail img:hover {
  border-color: #ffa500; /* 호버 시 강조 */
}


/* 중앙 이미지 영역 */
.image-viewer {
  width: 60%;
  background-color: #f6f6f6;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-viewer img {
  max-width: 80%;
  max-height: 80%;
  object-fit: contain;
  border-radius: 8px;
}

/* 우측 편집기 영역 */
.editor-placeholder {
  width: 20%;
  background-color: #f6f6f6;
  display: flex;
  align-items: center;
  justify-content: center;
}

.editor-placeholder {
}
</style>
