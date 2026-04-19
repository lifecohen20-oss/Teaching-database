import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def main():
    creds_json = json.loads(os.environ['GDRIVE_CREDENTIALS'])
    creds = service_account.Credentials.from_service_account_info(creds_json, scopes=['https://www.googleapis.com/auth/drive.readonly'])
    
    service = build('drive', 'v3', credentials=creds)
    folder_id = os.environ['FOLDER_ID']
    
    all_files = []
    
    # === התיקון למהירות שיא ===
    # הסרנו מכאן שדות כבדים ומיותרים כמו webViewLink ו-iconLink.
    # אנחנו מייצרים אותם לבד באתר! זה יקטין את הקובץ ב-70% וימנע שבירות.
    fields = "nextPageToken, files(id, name, mimeType, size, modifiedTime, thumbnailLink, parents, shortcutDetails)"
    
    print("מתחיל סריקה ראשית של הארכיון...")
    page_token = None
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

    scanned_folders = set()
    folders_to_scan = []
    
    for f in all_files:
        if f.get('mimeType') == 'application/vnd.google-apps.shortcut':
            details = f.get('shortcutDetails', {})
            if details.get('targetMimeType') == 'application/vnd.google-apps.folder':
                target_id = details.get('targetId')
                if target_id:
                    folders_to_scan.append(target_id)
                    
    if folders_to_scan:
        print(f"נמצאו {len(folders_to_scan)} קיצורי דרך לתיקיות. מתחיל סריקה עמוקה שלהן...")
        
    while folders_to_scan:
        current_folder_id = folders_to_scan.pop(0)
        if current_folder_id in scanned_folders:
            continue
        scanned_folders.add(current_folder_id)
        
        page_token = None
        try:
            while True:
                results = service.files().list(
                    q=f"'{current_folder_id}' in parents and trashed = false",
                    pageSize=1000,
                    fields=fields,
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                for item in items:
                    if not any(existing['id'] == item['id'] for existing in all_files):
                        all_files.append(item)
                        if item.get('mimeType') == 'application/vnd.google-apps.folder':
                            folders_to_scan.append(item['id'])
                            
                page_token = results.get('nextPageToken', None)
                if page_token is None:
                    break
        except Exception as e:
            print(f"לא ניתן לסרוק את התיקייה {current_folder_id}: {e}")

    print(f"הסריקה הושלמה בהצלחה. סך הכל {len(all_files)} פריטים.")

    database = {
        "root_folder_id": folder_id,
        "total_items": len(all_files),
        "files": all_files
    }

    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, separators=(',', ':'))
    
    print("קובץ database.json נוצר בהצלחה בפורמט סופר-מכווץ!")

if __name__ == '__main__':
    main()
