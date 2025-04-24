import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Define scope and credentials
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("resonant-hawk-457718-a1-20ad76e90527.json", scope)
client = gspread.authorize(creds)

# Open your sheet by URL or title
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1LF8Zk7BG6PSDb9-Zvw0MbagllDWVq9r7k8a35YaY3_0/edit?usp=sharing")

# Access the first worksheet
sheet = spreadsheet.sheet1

# Example: print all data
data = sheet.get_all_records()
print(data)
