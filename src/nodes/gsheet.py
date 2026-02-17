import os
import json
import pandas as pd
import gspread
# from google.auth import default
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.core.state import VCAgentState
from src.utils.VC_utils import template_id, google_cred_file

#------------------------WORKLOAD IDENTITY FEDERATION AUTH-----

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Lazy-loaded credentials and clients
_creds = None
_client = None
_drive_service = None


def _get_wif_credentials():
    """
    Uses Application Default Credentials.

    In GitHub Actions:
    - google-github-actions/auth@v2 sets GOOGLE_APPLICATION_CREDENTIALS
    - This loads the temporary WIF credentials automatically

    Locally:
    - Uses `gcloud auth application-default login` (if present)
    """
    global _creds
    if _creds is None:
        _creds = service_account.Credentials.from_service_account_file(
            google_cred_file,
            scopes=SCOPES
        )
    return _creds


def _get_gspread_client():
    """Lazily initialize gspread client."""
    global _client
    if _client is None:
        _client = gspread.authorize(_get_wif_credentials())
    return _client


def _get_drive_service():
    """Lazily initialize Google Drive service."""
    global _drive_service
    if _drive_service is None:
        _drive_service = build(serviceName="drive", version="v3", credentials=_get_wif_credentials())
    return _drive_service


#--------------------------------------------------------------

def export_to_sheets(state: VCAgentState,
                     foss_name: str,
                     language: str,
                     user_emails: list[str],
                     user_role: str = "writer"  # "writer" | "reader" | "commenter"
                     ) -> str:

    client = _get_gspread_client()
    drive_service = _get_drive_service()
    
    generated_sheet_name = f"VC-{foss_name}_{language}"
    print(f"Copying template to {generated_sheet_name}...")

    new_sheet = client.copy(template_id, title=generated_sheet_name)

    worksheet = new_sheet.sheet1

    worksheet.batch_clear(["A4:Z1000"])


    # df = pd.read_csv(f"results/temp_{foss_name}_{language}.csv")
    df = pd.DataFrame(state["final_table"])
    df = df.fillna("")
    data_to_upload = [df.columns.values.tolist()] + df.values.tolist()

    # 6. Update the Sheet
    # value_input_option='USER_ENTERED' ensures numbers/dates aren't stored as strings
    worksheet.update(values=data_to_upload, range_name="A3", value_input_option="USER_ENTERED")

    for email in user_emails:
        drive_service.permissions().create(
            fileId=new_sheet.id,
            body={
                "type": "user",
                "role": user_role,
                "emailAddress": email
            },
            sendNotificationEmail=True).execute()
        
        print (f"Sheet delivered to {email}")
    
    return new_sheet.url
    
def share_sheet(sheet_url: str, recipients: list[dict]):
    drive_service = _get_drive_service()
    
    # Extract sheet ID from URL
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    
    for recipient in recipients:
        email = recipient['email']
        role = recipient.get('role', 'writer')
        drive_service.permissions().create(
            fileId=sheet_id,
            body={
                "type": "user",
                "role": role,
                "emailAddress": email
            },
            sendNotificationEmail=True).execute()
        
        print(f"Sheet shared to {email} as {role}")
    
    return f"Sheet shared to {len(recipients)} recipients"