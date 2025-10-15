"""
Bloom 인지단계 분류를 위한 BloomBERT 모델 컨트롤러
"""

import torch
from transformers import DistilBertTokenizer, DistilBertModel
import torch.nn as nn
from pathlib import Path

# Bloom 인지단계 매핑
BLOOM_CATEGORIES = {
    0: "Remember",
    1: "Understand", 
    2: "Apply",
    3: "Analyse",
    4: "Evaluate",
    5: "Create"
}

class BloomBERT(nn.Module):
    """Bloom 인지단계 분류를 위한 BERT 모델"""
    
    def __init__(self, output_dim=6):
        super().__init__()
        self.bert = DistilBertModel.from_pretrained("distilbert-base-uncased")
        self.dropout = nn.Dropout(0.3)
        self.attention = nn.Linear(self.bert.config.hidden_size, 1)

        # two layer classifier
        self.classifier = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, output_dim),
        )

    def forward(self, input_ids, attention_mask=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        hidden_states = outputs.last_hidden_state  # [batch, seq_len, hidden]

        # attention pooling
        attn_weights = torch.softmax(self.attention(hidden_states).squeeze(-1), dim=1)
        pooled_output = torch.sum(hidden_states * attn_weights.unsqueeze(-1), dim=1)

        x = self.dropout(pooled_output)
        logits = self.classifier(x)
        return logits

class BloomClassifier:
    """Bloom 인지단계 분류기"""
    
    def __init__(self, model_path=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 모델 경로 설정
        if model_path is None:
            # 기본 모델 경로
            root_dir = Path(__file__).resolve().parents[1]
            model_path = root_dir / "models" / "bloombert_model.pt"
        
        # 모델 로드
        self.model = BloomBERT()
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        
        # 토크나이저 로드
        self.tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
        
        print(f"✅ BloomBERT 모델 로드 완료 (Device: {self.device})")
    
    def predict_bloom_category(self, text):
        """텍스트의 Bloom 인지단계를 예측"""
        try:
            # 텍스트 토큰화
            encodings = self.tokenizer(text, truncation=True, padding=True, return_tensors="pt")
            input_ids = encodings["input_ids"].to(self.device)
            attention_mask = encodings["attention_mask"].to(self.device)
            
            # 예측 수행
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                pred_class = int(torch.argmax(outputs, dim=1).cpu().numpy()[0])
            
            return BLOOM_CATEGORIES[pred_class]
            
        except Exception as e:
            print(f"⚠️ Bloom 분류 중 오류: {e}")
            return "Unknown"
    
    def predict_segments(self, segments):
        """세그먼트 리스트의 각 자막에 대해 Bloom 분류 수행"""
        print(f"\n🧠 Bloom 인지단계 분류 시작...")
        
        for i, segment in enumerate(segments):
            if hasattr(segment, 'subtitles') and segment.subtitles:
                # 자막 텍스트로 Bloom 분류
                bloom_category = self.predict_bloom_category(segment.subtitles)
                segment.bloom_category = bloom_category
                
                print(f"   세그먼트 {i+1}: {bloom_category}")
            else:
                segment.bloom_category = "Unknown"
                print(f"   세그먼트 {i+1}: 자막 없음")
        
        print("✅ Bloom 분류 완료!")
        return segments
