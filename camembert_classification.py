import torch
import psycopg2
import pickle
import time
from transformers import CamembertTokenizer, CamembertForSequenceClassification
from postgres import connect_db

# Charger modèle + tokenizer + encoder
model_path = "./cyia_camembert_model"
model = CamembertForSequenceClassification.from_pretrained(model_path)
tokenizer = CamembertTokenizer.from_pretrained(model_path)
model.eval()

with open("label_encoder.pkl", "rb") as f:
    label_encoder = pickle.load(f)

def predict(subject, body):
    text = f"Objet : {subject}\nCorps : {body}"
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predicted_index = torch.argmax(probs, dim=1).item()
        return label_encoder.inverse_transform([predicted_index])[0]

def fetch_unclassified_email():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, subject, body 
        FROM emails 
        WHERE category IS NULL 
        AND subject IS NOT NULL AND body IS NOT NULL 
        ORDER BY id ASC
        LIMIT 1;
    """)
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

def update_email_category(email_id, category):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE emails SET category = %s WHERE id = %s;", (category, email_id))
    conn.commit()
    cur.close()
    conn.close()

def monitor_emails():
    print("🔁 Surveillance des e-mails en cours...")
    while True:
        email = fetch_unclassified_email()
        if email:
            eid, subject, body = email
            print(f"\n📥 Nouveau mail ID {eid}")
            predicted_label = predict(subject, body)
            print(f"✅ Classé en : {predicted_label}")
            update_email_category(eid, predicted_label)
        else:
            print("⏳ Aucun nouveau mail... Attente de 30 secondes.")
            time.sleep(30)

if __name__ == "__main__":
    monitor_emails()
