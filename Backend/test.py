import torch
from transformers import DistilBertTokenizer, DistilBertModel
import torch.nn as nn

config = {
    "device": torch.device("cuda" if torch.cuda.is_available() else "cpu")
}

category_dict = {
    0: "Remember",
    1: "Understand",
    2: "Apply",
    3: "Analyse",
    4: "Evaluate",
    5: "Create"
}

class BloomBERT(nn.Module):
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

# 모델 객체 생성 후 state_dict 로드
bloombert_model = BloomBERT()
bloombert_model.load_state_dict(torch.load("./Backend/models/bloombert_model.pt", map_location=config["device"]))
bloombert_model.to(config["device"])

tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")

def predict_category(text, model, tokenizer, device):
    encodings = tokenizer(text, truncation=True, padding=True, return_tensors="pt")
    input_ids = encodings["input_ids"].to(device)
    attention_mask = encodings["attention_mask"].to(device)
    model.eval()
    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        pred_class = int(torch.argmax(outputs, dim=1).cpu().numpy()[0])
    return category_dict[pred_class]

# test_text -> summary로 변경
test_text = "이 모든 784개의 뉴런이 신경망의 입력층을 구성하게 됩니다. 출력층은 총 10개의 뉴런을 가지고 있습니다.\n각각의 뉴런은 0 부터 9 까지의 숫자를 대표하는데요, 이 뉴런들은 0과 1사이의 어떤 값을 취하고. 그 값은 뉴런이 대표하는 숫자와 입력값이 일치하는 정도를 나타냅니다. 그 값은 주어진 입력값과\n 각 뉴런이 대표하는 숫자 사이의 일치 정도를 나타냅니다. 입력층과 출력층 사이에는 숨겨진 층이라고 불리는 몇 개의 층들이 있는데요, 지금 당장은 이 층이 어떻게 숫자를 인식할 수 있는지 중요하지 않으므로 물음표 표시만 해놓고 넘어가도록 합시다. 이 신경망에선 각각 16개의 뉴런을 가진 두 개의 숨겨진 층을 사용할건데 솔직히 그냥 아무 숫자나 부른겁니다 두 개의 층을 선택한 이유는 조금 있다 이 구조를 구성할 방법 때문이고 그리고 16개는... 그냥 화면에 잘 들어가서 넣은 겁니다. 같은 역할을 하는 신경망의 형태는 더 많이 있습니다. 이 신경망은 기본적으로한 층에서의 활성화가 다음 층의 활성화를 유도하는 방식으로 작동합니다. 정보 처리에 있어서의 신경망의 가장 중요한 점은 도대체 어떻게 한 층에서의 활성화가 다른 층의 활성화를 불러일으키는지에 관한 점입니다. 이러한 과정은\n생물의 뉴런이 작동하는 방식과도 닮아있는데, 몇몇 뉴런의 활성화가\n다른 뉴런의 활성화를 수반한다는 점이죠. 제가 지금 보여드리는 신경망은\n이미 숫자를 인식하도록 훈련되어 있습니다. 사진의 픽셀인 784개에 해당하는 입력 뉴런들을\n모두 활성화 시킬 때, 이 때 활성화되는 뉴런들이 특정 패턴이 다음 층이 활성화 되게끔 합니다. 그 다음 열도 마찬가지로 활성화가 되고 마지막으로 출력 층에도 전달됩니다. 출력 층에서 가장 빛나는 뉴런이 이 신경망에서 선택된 출력값입니다."
predicted_category = predict_category(test_text, bloombert_model, tokenizer, config["device"])

print("Predicted Category:", predicted_category)