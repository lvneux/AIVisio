<template>
    <div class="image-generator">
      <div class="left-panel">
        <label for="prompt">prompt</label>
        <textarea
          id="prompt"
          v-model="prompt"
          placeholder="이미지 설명을 입력하세요"
        />
        <button @click="generateImage">이미지 생성</button>
      </div>
  
      <div class="preview-panel" v-if="imageUrl">
        <img :src="imageUrl" alt="Generated image" />
      </div>
    </div>
  </template>
  
  <style scoped>
  .image-generator {
    display: flex;
    gap: 2rem;
  }
  
  .left-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  textarea {
    width: 200px;
    height: 150px;
  }
  
  .preview-panel img {
    max-width: 500px;
    border: 1px solid #ccc;
  }
  </style>
  