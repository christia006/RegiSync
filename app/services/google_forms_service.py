from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
import logging

logger = logging.getLogger(__name__)

class GoogleFormsService:
    def __init__(self, client_secret_file, spreadsheet_id, scopes):
        self.client_secret_file = client_secret_file
        self.spreadsheet_id = spreadsheet_id
        self.scopes = scopes
        self.service = self._authenticate_google()

    def _authenticate_google(self):
        creds = None
        token_path = 'token.pickle' # Path to store the user's access and refresh tokens

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Google API credentials...")
                creds.refresh(Request())
            else:
                logger.info("Authorizing Google API for the first time or re-authorizing...")
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_file, self.scopes)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            logger.info("Google API credentials obtained and saved.")
        else:
            logger.info("Using existing Google API credentials.")

        return build('sheets', 'v4', credentials=creds)

    def get_form_responses(self, range_name='Sheet1!A:Z'): # Sesuaikan range sesuai sheet Anda
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            values = result.get('values', [])
            logger.info(f"Successfully retrieved {len(values)} rows from Google Sheet.")
            return values
        except Exception as e:
            logger.error(f"Error reading Google Sheet: {e}", exc_info=True)
            return []