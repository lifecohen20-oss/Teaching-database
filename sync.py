import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def main():
    creds_json = json.loads(os.environ['GDRIVE_CREDENTIALS'])
    creds = service_account.Credentials.from_service_account_info(creds_json, scopes=['https://www.googleapis.com/auth/drive.readonly'])
    
    service = build('drive', 'v3', credentials=creds)
    folder_id = os.environ['FOLDER_ID']
    
    all_raw_files = {}
    fields = "nextPageToken, files(id, name, mimeType, size, modifiedTime, thumbnailLink, parents, shortcutDetails)"
    
    print("מתחיל סריקה ראשית...")
    page_token = None
    while True:
        results = service.files().list(
            q="trashed = false",
            pageSize=1000,
            fields=fields,
            pageToken=page_token
        ).execute()
        
        for item in results.get('files', []):
            all_raw_files[item['id']] = item
            
        page_token = results.get('nextPageToken', None)
        if page_token is None:
            break

    scanned_folders = set()
    folders_to_scan = []
    
    # הוספת קיצורי הדרך לסריקה העמוקה
    for f in all_raw_files.values():
        if f.get('mimeType') == 'application/vnd.google-apps.shortcut':
            details = f.get('shortcutDetails', {})
            if details.get('targetMimeType') == 'application/vnd.google-apps.folder':
                tid = details.get('targetId')
                if tid: folders_to_scan.append(tid)
                    
    if folders_to_scan:
        print(f"נמצאו {len(folders_to_scan)} קיצורי דרך. סורק את תוכנם...")
        
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
                
                for item in results.get('files', []):
                    if item['id'] not in all_raw_files:
                        all_raw_files[item['id']] = item
                        mime = item.get('mimeType')
                        
                        # התיקון כאן: מזהה גם תיקיות רגילות וגם קיצורי דרך לתיקיות *בתוך* תיקיות אחרות
                        if mime == 'application/vnd.google-apps.folder':
                            folders_to_scan.append(item['id'])
                        elif mime == 'application/vnd.google-apps.shortcut':
                            details = item.get('shortcutDetails', {})
                            if details.get('targetMimeType') == 'application/vnd.google-apps.folder':
                                tid = details.get('targetId')
                                if tid: folders_to_scan.append(tid)
                            
                page_token = results.get('nextPageToken', None)
                if page_token is None:
                    break
        except Exception as e:
            print(f"התעלם מתיקייה {current_folder_id}: {e}")

    print(f"נסרקו סך הכל {len(all_raw_files)} פריטים. מכווץ למבנה מטריצה...")

    matrix_files = []
    for f in all_raw_files.values():
        mime = f.get('mimeType', '')
        if mime == 'application/vnd.google-apps.folder': mime = 'f'
        elif mime == 'application/vnd.google-apps.shortcut': mime = 's'
        
        parent = f.get('parents', [''])[0] if f.get('parents') else ''
        thumb = f.get('thumbnailLink', '')
        
        targetId = ''
        targetMime = ''
        if mime == 's':
            targetId = f.get('shortcutDetails', {}).get('targetId', '')
            tm = f.get('shortcutDetails', {}).get('targetMimeType', '')
            if tm == 'application/vnd.google-apps.folder': tm = 'f'
            targetMime = tm

        matrix_files.append([
            f.get('id', ''),
            f.get('name', ''),
            mime,
            f.get('size', ''),
            f.get('modifiedTime', ''),
            parent,
            thumb,
            targetId,
            targetMime
        ])

    database = {
        "root_folder_id": folder_id,
        "total_items": len(matrix_files),
        "format": "matrix",
        "files": matrix_files
    }

    with open('database.json', 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, separators=(',', ':'))
    
    print("קובץ database.json מבוסס מטריצה נוצר בהצלחה!")

if __name__ == '__main__':
    main()
