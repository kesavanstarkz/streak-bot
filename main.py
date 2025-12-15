import os
import base64
from flask import Flask, send_file, render_template, request, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI
import requests
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables from .env (for local development)
load_dotenv()

app = Flask(__name__)

# Telegram bot token (must be set in environment as TELEGRAM_BOT_TOKEN)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'jfif', 'bmp', 'tiff'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Twilio integration removed

# ---------------------------
# AZURE OPENAI CONFIG
# ---------------------------
# These values must be provided via environment variables in production.
azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")

azure_client = OpenAI(
    base_url=azure_endpoint,
    api_key=azure_api_key
)

# OCR Config
OCR_API_KEY = os.environ.get("OCR_API_KEY", "")
OCR_URL = "https://api.ocr.space/parse/image"

# Google Sheets Config
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
RANGE_NAME = os.environ.get("SHEET_RANGE_NAME", "Sheet1!A1")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_to_jpeg(image_path):
    """Convert image to JPEG format if it's in a different format"""
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Convert RGBA to RGB (for formats with transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create a white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Create JPEG path
        base_path = os.path.splitext(image_path)[0]
        jpeg_path = base_path + '_converted.jpeg'
        
        # Save as JPEG
        img.save(jpeg_path, 'JPEG', quality=95)
        
        # Remove original if it was a different format
        if not image_path.lower().endswith('.jpeg') and not image_path.lower().endswith('.jpg'):
            try:
                os.remove(image_path)
            except:
                pass
        
        return jpeg_path
    except Exception as e:
        # If conversion fails, return original path
        print(f"Conversion error: {e}")
        return image_path

def encode_image(image_path):
    """Encode image to base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def process_image_with_azure(image_path):
    """Process image with Azure GPT-4o Vision - Extract certificate name and provider"""
    try:
        # Basic config validation so we don't hit confusing connection errors
        if not azure_endpoint or not azure_api_key:
            return '{"name": "Error", "streak": "Error: Azure configuration missing (endpoint or API key)."}'

        image_base64 = encode_image(image_path)
        response = azure_client.chat.completions.create(
            model=azure_deployment,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are extracting data from a streak/certificate image. Find: 1) the full name of the person 2) the streak information (e.g., '43 days completed'). Return ONLY valid JSON in this exact format: {\\\"name\\\": \\\"<full name>\\\", \\\"streak\\\": \\\"<number> days completed\\\"}. Do not include markdown, backticks, explanation, or any extra text."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
        )
        result = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if result.startswith("```json"):
            result = result.replace("```json", "").replace("```", "").strip()
        elif result.startswith("```"):
            result = result.replace("```", "").strip()
        
        return result
    except Exception as e:
            return f'{{"name": "Error", "streak": "Error: {str(e)}"}}'

def process_image_with_ocr(image_path):
    """Process image with OCR Space API"""
    try:
        if not OCR_API_KEY:
            return "OCR processing error: OCR_API_KEY is not configured."

        with open(image_path, 'rb') as img:
            response = requests.post(
                OCR_URL,
                files={"filename": img},
                data={"apikey": OCR_API_KEY, "language": "eng"}
            )
        data = response.json()

        # Ensure expected keys are present
        if "ParsedResults" in data and data["ParsedResults"]:
            return data["ParsedResults"][0].get("ParsedText", "")

        # Fall back to returning the whole response for debugging
        return f"OCR processing error: Unexpected response format: {data}"
    except Exception as e:
        return f"OCR processing error: {str(e)}"

def save_to_sheets(azure_data, ocr_data=None):
    """Save extracted certificate data to Google Sheets with headers"""
    try:
        import json

        # Ensure spreadsheet id is provided
        if not SPREADSHEET_ID:
            return False, "Sheets error: SPREADSHEET_ID environment variable is not set."
        # Load Google service account credentials path from environment.
        # Default keeps backward compatibility for local use.
        service_account_path = os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "credientials/cred.json"
        )
        creds = Credentials.from_service_account_file(service_account_path)
        service = build("sheets", "v4", credentials=creds)
        
        # Parse Azure JSON response
        try:
            azure_json = json.loads(azure_data)
            name = azure_json.get("name", "Unknown")
            streak = azure_json.get("streak", "Unknown")
        except:
            name = "Parse Error"
            streak = azure_data
        
        # First, check if headers exist
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=RANGE_NAME
            ).execute()
            existing_values = result.get('values', [])
        except:
            existing_values = []
        
        # If no data exists or first row doesn't have headers, create them
        if not existing_values or len(existing_values) == 0:
            # Create headers
            headers = ["Name", "Streak"]
            header_body = {"values": [headers]}
            
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=RANGE_NAME,
                valueInputOption="RAW",
                body=header_body
            ).execute()
            
            # Now append the data
            row = [name, streak]
            
            values = [row]
            data_body = {"values": values}
            
            result = service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range="Sheet1!A2",  # Start from row 2 (after headers)
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=data_body
            ).execute()
        else:
            # Headers exist, just append data
            row = [name, streak]
            
            values = [row]
            data_body = {"values": values}
            
            result = service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=RANGE_NAME,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=data_body
            ).execute()
        
        return True, f"{result.get('updates').get('updatedRows')} rows updated"
    except Exception as e:
        return False, f"Sheets error: {str(e)}"

# Twilio webhook and helpers removed — WhatsApp/Twilio integration disabled

@app.route("/")
def index():
    return render_template('index.html')


def download_telegram_file(file_id):
    """Download file from Telegram by file_id and save to uploads folder"""
    try:
        if not TELEGRAM_BOT_TOKEN:
            print("TELEGRAM_BOT_TOKEN not set")
            return None

        resp = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        data = resp.json()
        if not data.get("ok"):
            print("getFile failed", data)
            return None

        file_path = data["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

        r = requests.get(file_url, stream=True)
        if r.status_code != 200:
            print("Failed to download file from Telegram", r.status_code)
            return None

        ext = os.path.splitext(file_path)[1] or ".jpg"
        filename = f"telegram_{int(__import__('time').time())}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

        return filepath
    except Exception as e:
        print("download_telegram_file error:", e)
        return None


def send_telegram_message(chat_id, text):
    try:
        if not TELEGRAM_BOT_TOKEN:
            print("TELEGRAM_BOT_TOKEN not set")
            return False
        payload = {"chat_id": chat_id, "text": text}
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)
        return r.status_code == 200
    except Exception as e:
        print("send_telegram_message error:", e)
        return False


@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.get_json(force=True)
        message = update.get('message') or update.get('edited_message')
        if not message:
            return '', 200

        chat_id = message['chat']['id']

        # handle photos
        if 'photo' in message:
            file_id = message['photo'][-1]['file_id']
            filepath = download_telegram_file(file_id)
            if not filepath:
                send_telegram_message(chat_id, 'Failed to download image.')
                return '', 200

            filepath = convert_to_jpeg(filepath)
            azure_result = process_image_with_azure(filepath)
            ocr_result = process_image_with_ocr(filepath)
            sheets_success, sheets_msg = save_to_sheets(azure_result, ocr_result)

            # prepare reply
            try:
                import json
                azure_json = json.loads(azure_result)
                name = azure_json.get('name', 'Unknown')
                streak = azure_json.get('streak', 'Unknown')
                reply = f"✅ Processed.\n\nName: {name}\nStreak: {streak}\nSaved: {sheets_success}"
            except Exception:
                reply = f"Processed. Result: {azure_result}"

            send_telegram_message(chat_id, reply)
            return '', 200

        # non-photo messages
        send_telegram_message(chat_id, 'Please send an image to process.')
        return '', 200
    except Exception as e:
        print('telegram_webhook error:', e)
        return '', 500

@app.route("/upload", methods=['POST'])
def upload_file():
    """Handle image upload and process with Azure"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Convert to JPEG if needed
        filepath = convert_to_jpeg(filepath)
        
        # Process with Azure
        azure_result = process_image_with_azure(filepath)
        
        # Process with OCR
        ocr_result = process_image_with_ocr(filepath)
        
        # Save to Google Sheets
        sheets_success, sheets_msg = save_to_sheets(azure_result, ocr_result)
        
        return jsonify({
            'success': True,
            'azure_result': azure_result,
            'ocr_result': ocr_result,
            'sheets_saved': sheets_success,
            'sheets_message': sheets_msg,
            'filename': filename
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/process-default", methods=['GET'])
def process_default():
    """Process the default image"""
    image_path = "image/with_streaks_cropped.jpg"
    
    if not os.path.exists(image_path):
        return jsonify({'error': 'Default image not found'}), 404
    
    # Process with Azure
    azure_result = process_image_with_azure(image_path)
    
    # Process with OCR
    ocr_result = process_image_with_ocr(image_path)
    
    # Save to Google Sheets
    sheets_success, sheets_msg = save_to_sheets(azure_result, ocr_result)
    
    return jsonify({
        'azure_result': azure_result,
        'ocr_result': ocr_result,
        'sheets_saved': sheets_success,
        'sheets_message': sheets_msg
    }), 200

if __name__ == '__main__':
    # Get port from environment variable (Render sets PORT)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)