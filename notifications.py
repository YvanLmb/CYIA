from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os

# Scopes Gmail nécessaires
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail(user_id="default"):
    token_file = f'token_{user_id}.json'
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    return build('gmail', 'v1', credentials=creds)

def start_watch(service):
    request = {
        'labelIds': ['INBOX'],  # On surveille juste la boîte principale
        'topicName': 'projects/cyia-457413/topics/gmail-push-notif'  # 🔥 Remplacer ici TON vrai ID projet
    }
    response = service.users().watch(userId='me', body=request).execute()
    print('🔔 Watch démarré :', response)

if __name__ == '__main__':
    user_id = input("🔐 Entrez ton user_id pour Gmail (ex: default) : ")
    service = authenticate_gmail(user_id=user_id)
    start_watch(service)
