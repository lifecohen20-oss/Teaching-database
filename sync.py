import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def main():
    # קריאת אישורי ההתחברות מהסודות של גיטהאב
    creds_json = json.loads(os.environ['GDRIVE_CREDENTIALS'])
    creds = service_account.Credentials.from_service_account_info(creds_json, scopes=['[https://www.googleapis.com/auth/drive.readonly](https://www.googleapis.com/auth/drive.readonly)'])
    
    # התחברות לדרייב
    service = build('drive', 'v3', credentials=creds)
    folder_id = os.environ['FOLDER_ID']
    
    all_files = []
    page_token = None
    
    # הגדרת השדות שאנחנו רוצים לשלוף
    fields = "nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, webContentLink, thumbnailLink, hasThumbnail, iconLink, parents)"
    
    # מכיוון שהרובוט משותף רק עם תיקיית הארכיון, אנחנו שולפים פשוט הכל!
    print("מתחיל בסריקת הקבצים...")
    while True:
        results = service.files().list(
            q="trashed = false",
            pageSize=1000,
            fields=fields,
            pageToken=page_token
        ).execute()
        
        items = results.get('files', [])
        all_files.extend(items)
        
        page_token = results.get('nextPageToken', None)
        if page_token is None:
            break

    print(f"נסרקו בהצלחה {len(all_files)} קבצים ותיקיות.")

    # בניית אובייקט הנתונים
    database = {
        "root_folder_id": folder_id,
        "total_items": len(all_files),
        "files": all_files
    }

    # שמירה לקובץ
    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
    
    print("קובץ database.json נוצר בהצלחה!")

if __name__ == '__main__':
    main()
