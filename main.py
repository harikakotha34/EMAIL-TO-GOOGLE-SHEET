from gmail_service import get_gmail_service
from googleapiclient.discovery import build
import base64, os

# Google Sheet details
SPREADSHEET_ID = '1AF6gcNjHvb3mdJ_cH-UskGa3iwa1Eq7I-CvFP2HEUDA'
SHEET_RANGE = 'Emails!A1'

processed = set()
if os.path.exists('processed.txt'):
    with open('processed.txt') as f:
        processed = set(f.read().splitlines())

gmail_service = get_gmail_service()

# Sheets service uses the same token
sheets_service = build('sheets', 'v4', credentials=gmail_service._http.credentials)

# Fetch unread emails
results = gmail_service.users().messages().list(
    userId='me',
    q='is:unread in:inbox'
).execute()

messages = results.get('messages', [])
print("Unread emails:", len(messages))

for msg in messages:
    if msg['id'] in processed:
        continue

    message = gmail_service.users().messages().get(
        userId='me', id=msg['id'], format='full'
    ).execute()

    # Extract headers
    headers = message['payload']['headers']
    sender = subject = date = ""
    for h in headers:
        if h['name'] == 'From':
            sender = h['value']
        elif h['name'] == 'Subject':
            subject = h['value']
        elif h['name'] == 'Date':
            date = h['value']

    # Extract plain text body
    body = ""
    for part in message['payload'].get('parts', []):
        if part['mimeType'] == 'text/plain' and part['body'].get('data'):
            body = base64.urlsafe_b64decode(part['body']['data']).decode()

    # Append to Google Sheets
    values = [[sender, subject, date, body]]
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=SHEET_RANGE,
        valueInputOption='RAW',
        body={'values': values}
    ).execute()

    # Mark email as read
    gmail_service.users().messages().modify(
        userId='me',
        id=msg['id'],
        body={'removeLabelIds': ['UNREAD']}
    ).execute()

    processed.add(msg['id'])

with open('processed.txt', 'w') as f:
    f.write('\n'.join(processed))

print("Emails processed and added to Google Sheets successfully!")
print(messages)
