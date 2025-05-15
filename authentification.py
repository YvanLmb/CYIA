from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail(user_id="yvan"):
    creds = None
    token_file = f"token_{user_id}.json"

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

if __name__ == "__main__":
    authenticate_gmail(user_id="yvan")
    print("✅ Token généré avec succès.")
