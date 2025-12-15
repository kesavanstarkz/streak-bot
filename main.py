import os
import base64
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from openai import OpenAI
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from PIL import Image
from dotenv import load_dotenv

# ---------------------------
# LOAD ENV
# ---------------------------
load_dotenv()

app = Flask(__name__)

# ---------------------------
# CONFIG
# ---------------------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "webp", "bmp",
    "jfif", "tiff", "tif"
}

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_CREDS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

azure_client = OpenAI(
    base_url=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY
)

# ---------------------------
# HELPERS
# ---------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_valid_image(path):
    try:
        Image.open(path).verify()
        return True
    except Exception:
        return False


def convert_to_jpeg(path):
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")

    new_path = path.rsplit(".", 1)[0] + ".jpg"
    img.save(new_path, "JPEG", quality=95)

    if new_path != path:
        os.remove(path)

    return new_path


def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------
# GPT-4o IMAGE PROCESSING
# ---------------------------
def process_image_with_azure(image_path):
    image_base64 = encode_image(image_path)

    response = azure_client.chat.completions.create(
        model=AZURE_DEPLOYMENT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """
Extract data from this streak screenshot.

Return ONLY valid JSON:
{
  "name": "<full name>",
  "platform": "Mimo | Elevate | Unknown",
  "streak": "<number>"
}
"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    return json.loads(raw)


# ---------------------------
# GOOGLE SHEETS LOGIC (SEPARATE SHEETS)
# ---------------------------
def save_to_sheets(data):
    creds = Credentials.from_service_account_file(GOOGLE_CREDS)
    service = build("sheets", "v4", credentials=creds)
    sheet_api = service.spreadsheets()

    today = datetime.now().strftime("%Y-%m-%d")

    name = data.get("name", "Unknown")
    platform = data.get("platform", "Unknown")
    streak = data.get("streak", "")

    # ✅ DEFAULT TO MIMO
    if platform not in ["Mimo", "Elevate"]:
        platform = "Mimo"

    # ✅ SELECT SHEET
    sheet_name = "Sheet2" if platform == "Elevate" else "Sheet1"

    result = sheet_api.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=sheet_name
    ).execute()

    values = result.get("values", [])

    # Create header if empty
    if not values:
        headers = ["Name", "Streak Date", "Streak Number"]
        sheet_api.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": [headers]}
        ).execute()
        values = [headers]

    # Find existing user
    row_index = None
    for i in range(1, len(values)):
        if values[i][0] == name:
            row_index = i + 1
            break

    new_row = [name, today, streak]

    # New user
    if not row_index:
        sheet_api.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=sheet_name,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [new_row]}
        ).execute()
        return f"Saved to {sheet_name} (new user)"

    # Existing user → append as new row (history preserved)
    sheet_api.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=sheet_name,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [new_row]}
    ).execute()

    return f"Saved to {sheet_name} (existing user)"


# ---------------------------
# ROUTES
# ---------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type"}), 400

        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        if not is_valid_image(path):
            os.remove(path)
            return jsonify({"error": "File is not a valid image"}), 400

        path = convert_to_jpeg(path)

        data = process_image_with_azure(path)
        status = save_to_sheets(data)

        return jsonify({
            "success": True,
            "name": data["name"],
            "platform": data.get("platform", "Mimo"),
            "streak": data["streak"],
            "saved_to": status
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
