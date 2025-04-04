<template>
  <div class="image-generator">
    <div class="left-panel">
      <label for="prompt">prompt</label>
      <textarea
        id="prompt"
        v-model="prompt"
        placeholder="이미지 설명을 입력하세요"
      ></textarea>

      <button type="button" @click="generateImages">이미지 생성</button>

      <!-- 모델 선택 -->
      <label for="model">선택 모델:</label>
      <select v-model="selectedModel" id="model">
        <option disabled value="">다음 중 하나를 선택하세요</option>
        <option>모델A</option>
        <option>모델B</option>
      </select>

      <!-- 이미지 썸네일 목록 -->
      <div class="thumbnail-grid">
        <div
          v-for="(img, index) in images"
          :key="index"
          class="thumbnail"
          @click="selectImage(img)"
        >
          <img :src="img" alt="generated image thumbnail" />
        </div>
      </div>
    </div>

    <!-- 가운데 미리보기 영역 -->
    <div class="preview-panel">
      <div class="image-frame" v-if="selectedImage">
        <img :src="selectedImage" alt="Selected image" />
      </div>
    </div>

    <!-- 우측 영역은 그대로 -->
    <div class="editor-placeholder">
      편집기능 추가 예정
    </div>
  </div>
</template>


<script lang="ts">
import { defineComponent, ref } from 'vue'

export default defineComponent({
  name: 'ImageGenerator',
  setup() {
    const prompt = ref('')
    const selectedModel = ref('')
    const images = ref<string[]>([]) // 생성된 이미지 목록
    const selectedImage = ref<string | null>(null) // 선택된 이미지

    // 더미 이미지 경로로 가정
    const dummyImageUrls = [
      '/assets/dummy1.jpg',
      '/assets/dummy2.jpg',
      '/assets/dummy3.jpg',
      '/assets/dummy4.jpg',
      '/assets/dummy5.jpg',
      '/assets/dummy6.jpg',
    ]

    const generateImages = () => {
      if (!prompt.value.trim()) return
      // 나중에 백엔드 연동 시, 서버에서 받아온 이미지로 대체
      images.value = dummyImageUrls
      selectedImage.value = null // 초기화
    }

    const selectImage = (img: string) => {
      selectedImage.value = img
    }

    return {
      prompt,
      selectedModel,
      images,
      selectedImage,
      generateImages,
      selectImage,
    }
  },
})
</script>



<style scoped>
.image-generator {
  display: flex;
  height: 100vh;
}

.left-panel {
  width: 20%;
  padding: 20px;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.preview-panel {
  width: 60%;
  background-color: #f6f6f6;
  display: flex;
  align-items: center;
  justify-content: center;
}

.editor-placeholder {
  width: 20%;
  background-color: #f6f6f6;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thumbnail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 10px;
}

.thumbnail img {
  width: 100%;
  height: auto;
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 6px;
  transition: border 0.2s;
}

.thumbnail img:hover {
  border-color: #007bff;
}

.image-frame img {
  max-width: 80%;
  max-height: 80%;
  object-fit: contain;
  border-radius: 8px;
}
</style>
