import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Scopes Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail(user_id="yvan"):
    """Connexion Gmail API"""
    token_file = f'token_{user_id}.json'
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        raise Exception("Token invalide ou manquant. Lance d'abord l'authentification Gmail.")
    return build('gmail', 'v1', credentials=creds)

# --- MAIN ---
if __name__ == "__main__":
    user_id = "yvan"  # 🔥 Le nom de ton fichier token_yvan.json
    topic_name = "projects/cyia-457413/topics/gmail-push-notif"  # 🔥 Ton topic Pub/Sub
    webhook_url = "https://cyia-457413.ew.r.appspot.com/notification"  # 🔥 Ton URL déployée

    service = authenticate_gmail(user_id=user_id)

    # 🛠️ Nouvelle demande de Watch
    watch_request = {
        'labelIds': ['INBOX'],
        'topicName': topic_name,
        'pushConfig': {
            'pushEndpoint': webhook_url
        }
    }

    response = service.users().watch(userId='me', body=watch_request).execute()
    print("✅ Watch mis à jour avec succès :", response)
