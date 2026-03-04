import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pymongo
from dotenv import load_dotenv

# load_dotenv()

# Google Sheet
client: gspread.Client = gspread.authorize(
    ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ['GOOGLE_CLOUD_API_KEY']),
        [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
    )
)
google_sheet = client.open_by_key('1S3xryeE_3ZrbpjTeT5_DGPPLNu5iQBSjvlhEtY1UTLI')

# MongoDB
client = pymongo.MongoClient(f'mongodb+srv://{os.environ["MONGO_DB_USERNAME"]}:{os.environ["MONGO_DB_PASSWORD"]}@cluster0.rm0hdee.mongodb.net/')
db = client['fwmsbl']
