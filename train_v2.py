import json
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import T5ForConditionalGeneration, T5Tokenizer
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
import warnings
warnings.filterwarnings("ignore")

with open("aug_train.json") as f: train_data = json.load(f)
with open("aug_val.json") as f: val_data = json.load(f)

device = torch.device("cpu")
print(f"Using device: {device}")
print(f"Train: {len(train_data)} | Val: {len(val_data)}")

model_name = "google/flan-t5-base"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name).to(device)

class MeetingDataset(Dataset):
    def __init__(self, data, tokenizer, max_input=256, max_target=100):
        self.data = data
        self.tokenizer = tokenizer
        self.max_input = max_input
        self.max_target = max_target
    def __len__(self):
        return len(self.data)
    def __getitem__(self, idx):
        item = self.data[idx]
        inputs = self.tokenizer(item["input"], max_length=self.max_input, truncation=True, padding="max_length", return_tensors="pt")
        targets = self.tokenizer(item["target"], max_length=self.max_target, truncation=True, padding="max_length", return_tensors="pt")
        labels = targets["input_ids"].squeeze()
        labels[labels == self.tokenizer.pad_token_id] = -100
        return {"input_ids": inputs["input_ids"].squeeze(), "attention_mask": inputs["attention_mask"].squeeze(), "labels": labels}

train_dataset = MeetingDataset(train_data, tokenizer)
val_dataset = MeetingDataset(val_data, tokenizer)
train_loader = DataLoader(train_dataset, batch_size=1, shuffle=True, num_workers=0)
val_loader = DataLoader(val_dataset, batch_size=1, num_workers=0)
print(f"Train batches: {len(train_loader)} | Val batches: {len(val_loader)}")

optimizer = AdamW(model.parameters(), lr=3e-4)
scheduler = ReduceLROnPlateau(optimizer, mode='min', patience=1, factor=0.5)
EPOCHS = 5
best_val_loss = float("inf")

for epoch in range(EPOCHS):
    model.train()
    total_loss = 0
    for i, batch in enumerate(train_loader):
        optimizer.zero_grad()
        outputs = model(input_ids=batch["input_ids"].to(device), attention_mask=batch["attention_mask"].to(device), labels=batch["labels"].to(device))
        loss = outputs.loss
        if torch.isnan(loss):
            del outputs
            continue
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        total_loss += loss.item()
        del outputs
        if i % 50 == 0:
            print(f"  Epoch {epoch+1} | Batch {i}/{len(train_loader)} | Loss: {total_loss/(i+1):.4f}")

    model.eval()
    val_loss = 0
    with torch.no_grad():
        for batch in val_loader:
            outputs = model(input_ids=batch["input_ids"].to(device), attention_mask=batch["attention_mask"].to(device), labels=batch["labels"].to(device))
            val_loss += outputs.loss.item()
            del outputs

    avg_val = val_loss / len(val_loader)
    avg_train = total_loss / len(train_loader)
    scheduler.step(avg_val)
    print(f"Epoch {epoch+1}/{EPOCHS} | Train Loss: {avg_train:.4f} | Val Loss: {avg_val:.4f}")

    if avg_val < best_val_loss:
        best_val_loss = avg_val
        model.save_pretrained("my_meeting_model_v3")
        tokenizer.save_pretrained("my_meeting_model_v3")
        print(f"   Best model saved (val loss: {best_val_loss:.4f})")

print(f"Done. Best val loss: {best_val_loss:.4f}")
