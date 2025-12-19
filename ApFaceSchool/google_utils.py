import os
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
SERVICE_ACCOUNT_FILE = 'C:\\PrjtEcole\\credentials.json'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'ApFaceSchool', 'credentials.json')

from google.oauth2 import service_account

def get_calendar_service():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'C:\\PrjtEcole\\credentials.json'  # ← adapte si besoin

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )

    service = build('calendar', 'v3', credentials=credentials)
    return service




#-----------------------



# def get_calendar_service():
#     creds = Credentials.from_authorized_user_file('credentials.json')
#     service = build('calendar', 'v3', credentials=creds)
#     return service



#------------------------

# def get_calendar_service():
#     creds = None
#     token_path = os.path.join(settings.BASE_DIR, 'token.json')
#     cred_path = os.path.join(settings.BASE_DIR, 'credentials.json')
#
#     if os.path.exists(token_path):
#         creds = Credentials.from_authorized_user_file(token_path, SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
#             creds = flow.run_local_server(port=0)
#         # Enregistrer le token pour réutilisation
#         with open(token_path, 'w') as token_file:
#             token_file.write(creds.to_json())
#
#     service = build('calendar', 'v3', credentials=creds)
#     return service

def create_meet_event(summary, description, start_dt, end_dt, attendees_emails=None, timezone='UTC'):
    """
    Crée un événement Google Calendar avec lien Google Meet (conference)
    """
    service = get_calendar_service()

    event_body = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': timezone,
        },
        'attendees': [{'email': e} for e in attendees_emails] if attendees_emails else [],
        'conferenceData': {
            'createRequest': {
                'requestId': str(uuid.uuid4()),
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                }
            }
        }
    }

    created_event = service.events().insert(
        calendarId='primary',
        body=event_body,
        conferenceDataVersion=1
    ).execute()

    meet_link = created_event.get('hangoutLink')
    html_link = created_event.get('htmlLink')
    return {'meet_link': meet_link, 'html_link': html_link}
