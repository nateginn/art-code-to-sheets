# pdf_to_sheets/sheets_manager.py

from google.oauth2 import service_account
from googleapiclient.discovery import build

class SheetsManager:
   def __init__(self, credentials_path):
       self.credentials_path = credentials_path
       self.scopes = [
           'https://www.googleapis.com/auth/spreadsheets',
           'https://www.googleapis.com/auth/drive'
       ]
       self._authenticate()

   def _authenticate(self):
       """Authenticate with Google Sheets API"""
       try:
           credentials = service_account.Credentials.from_service_account_file(
               self.credentials_path, scopes=self.scopes)
           self.service = build('sheets', 'v4', credentials=credentials)
           self.drive_service = build('drive', 'v3', credentials=credentials)
           print("Authentication successful")
           return True
       except Exception as e:
           print(f"Authentication error: {str(e)}")
           return False

   def check_sheet_exists(self, spreadsheet_id):
       """Check if spreadsheet exists and is accessible"""
       try:
           self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
           return True
       except Exception:
           return False

   def create_sheet(self, title):
       """Create a new Google Sheet with headers and sharing permissions"""
       try:
           spreadsheet = {
               'properties': {
                   'title': title
               }
           }
           spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
           spreadsheet_id = spreadsheet['spreadsheetId']
           
           # Share the spreadsheet
           try:
               permission = {
                   'type': 'user',
                   'role': 'writer',
                   'emailAddress': 'growyourbiz4ever@gmail.com'
               }
               self.drive_service.permissions().create(
                   fileId=spreadsheet_id,
                   body=permission
               ).execute()
           except Exception as e:
               print(f"Error sharing spreadsheet: {str(e)}")
           
           return spreadsheet_id
       except Exception as e:
           print(f"Error creating sheet: {str(e)}")
           return None

   def update_sheet(self, spreadsheet_id, rows):
       """Update sheet with data"""
       try:
           print(f"Updating sheet with {len(rows)} rows")
           # Format data for sheets API
           values = rows
            
           # Clear existing content
           range_name = 'A1:Z1000'  # Adjust range as needed
           self.service.spreadsheets().values().clear(
               spreadsheetId=spreadsheet_id,
               range=range_name
           ).execute()
            
           # Update with new data
           body = {
               'values': values,
               'majorDimension': 'ROWS'
           }
            
           result = self.service.spreadsheets().values().update(
               spreadsheetId=spreadsheet_id,
               range='A1',
               valueInputOption='RAW',
               body=body
           ).execute()
            
           print(f"Updated {result.get('updatedCells')} cells")
            
           # Format header row
           requests = []
           requests.append({
               'repeatCell': {
                   'range': {
                       'sheetId': 0,
                       'startRowIndex': 0,
                       'endRowIndex': 1,
                       'startColumnIndex': 0,
                       'endColumnIndex': len(rows[0])
                   },
                   'cell': {
                       'userEnteredFormat': {
                           'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8},
                           'textFormat': {'bold': True}
                       }
                   },
                   'fields': 'userEnteredFormat(backgroundColor,textFormat)'
               }
           })
            
           # Auto-resize columns
           requests.append({
               'autoResizeDimensions': {
                   'dimensions': {
                       'sheetId': 0,
                       'dimension': 'COLUMNS',
                       'startIndex': 0,
                       'endIndex': len(rows[0])
                   }
               }
           })
            
           self.service.spreadsheets().batchUpdate(
               spreadsheetId=spreadsheet_id,
               body={'requests': requests}
           ).execute()
            
           return True
       except Exception as e:
           print(f"Error updating sheet: {str(e)}")
           return False

   def highlight_skipped_rows(self, spreadsheet_id, skipped_rows):
       """Highlight skipped patient rows"""
       try:
           requests = []
           for row_index in skipped_rows:
               requests.append({
                   'repeatCell': {
                       'range': {
                           'sheetId': 0,
                           'startRowIndex': row_index + 1,  # +1 for header row
                           'endRowIndex': row_index + 2
                       },
                       'cell': {
                           'userEnteredFormat': {
                               'backgroundColor': {'red': 1, 'green': 0.9, 'blue': 0.9}
                           }
                       },
                       'fields': 'userEnteredFormat.backgroundColor'
                   }
               })
           
           if requests:
               self.service.spreadsheets().batchUpdate(
                   spreadsheetId=spreadsheet_id,
                   body={'requests': requests}
               ).execute()
           
           return True
       except Exception as e:
           print(f"Error highlighting rows: {str(e)}")
           return False

   def append_row(self, spreadsheet_id, values):
       """Append a row to the sheet"""
       try:
           # First check if sheet exists
           if not self.check_sheet_exists(spreadsheet_id):
               print("Spreadsheet not found or not accessible. Creating new sheet...")
               new_id = self.create_sheet("Patient Records")
               if new_id:
                   spreadsheet_id = new_id
               else:
                   return False

           # Add data
           body = {
               'values': [values],
               'range': 'A1'
           }
           result = self.service.spreadsheets().values().append(
               spreadsheetId=spreadsheet_id,
               range='A1',
               valueInputOption='USER_ENTERED',
               insertDataOption='INSERT_ROWS',
               body=body
           ).execute()
           print(f"Row appended successfully")
           return True
       except Exception as e:
           print(f"Error appending row: {str(e)}")
           return False

   def clear_invalid_sheet_id(self, config):
       """Clear invalid spreadsheet ID from config"""
       config.set('active_spreadsheet_id', None)

   def get_sheet_url(self, spreadsheet_id):
       """Get the URL for a spreadsheet"""
       return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
