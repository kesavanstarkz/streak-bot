import os

from flask import Flask, send_file
import requests
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


app = Flask(__name__)

# Use environment variable for OCR API key (do not hardcode in repo)
import os
API_KEY = os.environ.get("OCR_API_KEY", "")
url = "https://api.ocr.space/parse/image"
image_path = "image/with_streaks_cropped.jpg"

# @app.route("/")
# def index():
#     return send_file('src/index.html')

@app.route("/")
def imgText():

    with open(image_path, 'rb') as img:
        response = requests.post(
            url,
            files={"filename": img},
            data={"apikey": API_KEY, "language": "eng"}
        )
    result_image=response.json()["ParsedResults"][0]["ParsedText"]

    
    # SPREADSHEET_ID = "1oQq7m0qMQadxeDZBGER4WXUvI7iwk2yM-yzKCi82pS4"
    # RANGE_NAME = "Sheet1!A1"

    # creds = Credentials.from_service_account_file("credientials/cred.json")
    # service = build("sheets", "v4", credentials=creds)

    # values = [["Hello", "This", "is", "Row 1"]]
    # body = {"values": values}

    # result = service.spreadsheets().values().update(
    #     spreadsheetId=SPREADSHEET_ID,
    #     range=RANGE_NAME,
    #     valueInputOption="RAW",
    #     body=body
    # ).execute()

    # print(f"{result.get('updatedCells')} cells updated.")
    # return result 
    SPREADSHEET_ID = "1oQq7m0qMQadxeDZBGER4WXUvI7iwk2yM-yzKCi82pS4"
    RANGE_NAME = "Sheet1!A1"

    creds = Credentials.from_service_account_file("credientials/cred.json")
    service = build("sheets", "v4", credentials=creds)

    values = [[result_image]]  # inserting OCR extracted text
    body = {"values": values}

    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

    print(f"Data inserted successfully!")
    return "Updated successfully..."