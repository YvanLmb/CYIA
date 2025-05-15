import os.path
import base64
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from transformers import CamembertTokenizer, CamembertForSequenceClassification
import torch
import pickle
from postgres import connect_db

# Scopes Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Charger modèle et tokenizer
model_path = "./cyia_camembert_model"
model = CamembertForSequenceClassification.from_pretrained(model_path)
tokenizer = CamembertTokenizer.from_pretrained(model_path)
model.eval()

# Label encoder
with open("label_encoder.pkl", "rb") as f:
    label_encoder = pickle.load(f)

def authenticate_gmail(user_id="default"):
    token_file = f'token_{user_id}.json'
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_email_body(payload):
    if 'data' in payload.get('body', {}):
        data = payload['body']['data']
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    elif 'parts' in payload:
        for part in payload['parts']:
            result = get_email_body(part)
            if result:
                return result
    return ""

def predict_category(subject, body):
    text = f"Objet : {subject}\nCorps : {body}"
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predicted_index = torch.argmax(probs, dim=1).item()
        return label_encoder.inverse_transform([predicted_index])[0]

def save_email(gmail_id, sender, subject, body, received_at, category):
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO emails (gmail_id, sender, subject, body, received_at, category)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (gmail_id) DO NOTHING;
        """, (gmail_id, sender, subject, body, received_at, category))
        conn.commit()
        print("✅ Email enregistré avec catégorie :", category)
    except Exception as e:
        print("❌ Erreur BDD :", e)
    finally:
        cur.close()
        conn.close()

def get_existing_ids():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT gmail_id FROM emails;")
    ids = set([row[0] for row in cur.fetchall()])
    cur.close()
    conn.close()
    return ids

def monitor_inbox(service, check_interval=60):
    print("🔁 Surveillance de la boîte mail...")
    known_ids = get_existing_ids()

    while True:
        response = service.users().messages().list(userId='me', maxResults=50).execute()
        messages = response.get('messages', [])

        for msg_info in messages:
            msg_id = msg_info['id']
            if msg_id in known_ids:
                continue  # déjà traité

            msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

            subject = next((h['value'] for h in msg['payload']['headers'] if h['name'] == 'Subject'), 'Pas de sujet')
            sender = next((h['value'] for h in msg['payload']['headers'] if h['name'] == 'From'), 'Expéditeur inconnu')
            date_str = next((h['value'] for h in msg['payload']['headers'] if h['name'] == 'Date'), None)
            received_at = parsedate_to_datetime(date_str) if date_str else None
            body = get_email_body(msg['payload'])

            category = predict_category(subject, body)

            save_email(msg_id, sender, subject, body, received_at, category)
            known_ids.add(msg_id)

        print(f"⏳ Attente {check_interval}s avant le prochain check...")
        time.sleep(check_interval)


