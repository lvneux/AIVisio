<template>
  <div class="container">
    <!-- 좌측 영역 -->
    <div class="left-panel">
      <!-- 로고 이미지 -->
      <img src="@/assets/aivisio_logo.png" alt="AIVISIO Logo" class="logo" />

      <!-- Prompt 입력 영역 -->
      <div class="prompt-box">
        <label for="prompt" class="prompt-label">prompt</label>
        <textarea
          id="prompt"
          v-model="prompt"
          placeholder="이미지 설명을 입력하세요"
        ></textarea>

        <!-- 이미지 버튼 (기능은 그대로) -->
        <img
          src="@/assets/btn_create_image.png"
          alt="Create Image"
          class="create-btn"
          @click="generateImage"
        />
      </div>
    </div>

    <!-- 가운데 이미지 출력 영역 -->
    <div class="image-viewer">
      <img v-if="imageUrl" :src="imageUrl" alt="Generated" />
    </div>

    <!-- 우측 편집기 영역 -->
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
    const imageUrl = ref('')

    const generateImage = () => {
      if (!prompt.value.trim()) return
      imageUrl.value = `https://via.placeholder.com/512x512.png?text=${encodeURIComponent(prompt.value)}`
    }

    return {
      prompt,
      imageUrl,
      generateImage,
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
  color: #333;
  font-size: 14px;
  padding: 20px;
  text-align: center;
}
</style>
