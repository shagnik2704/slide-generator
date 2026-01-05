import pandas as pd
import gspread
from google.auth import default
from googleapiclient.discovery import build
from state import AgentState
from utils import template_id
from inputs import *


#------------------------AUTH---------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds, _ = default(scopes=SCOPES)
client = gspread.authorize(creds)
drive_service = build(serviceName="drive",version="v3",credentials=creds)

#--------------------------------------------------------------

def export_to_sheets(state: AgentState,
                     foss_name: str,
                     language: str,
                     user_emails: list[str],
                     user_role: str = "writer"  # "writer" | "reader" | "commenter"
                     ) -> str:

    generated_sheet_name = f"VC-{foss_name}_{language}"
    print(f"Copying template to {generated_sheet_name}...")

    new_sheet = client.copy(template_id, title=generated_sheet_name)

    worksheet = new_sheet.sheet1

    worksheet.batch_clear(["A3:Z1000"])


    # df = pd.read_csv(f"results/temp_{foss_name}_{language}.csv")
    df = pd.DataFrame(state["final_table"])
    df = df.fillna("")
    data_to_upload = [df.columns.values.tolist()] + df.values.tolist()

    # 6. Update the Sheet
    # value_input_option='USER_ENTERED' ensures numbers/dates aren't stored as strings
    worksheet.update(values=data_to_upload, range_name="A2", value_input_option="USER_ENTERED")

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
    
# import json
# with open("logs/final_output.json","r") as f:
#     state = json.load(f)

# export_to_sheets(state=state,
#                  foss_name=foss_name,
#                  language=language,
#                  user_email="aayush.231ee101@nitk.edu.in")