# Deployment Guide for Render.com

## Step 1: Prepare Your Repository

1. **Initialize Git** (if not already done):

```bash
git init
git add .
git commit -m "Initial commit"
```

2. **Push to GitHub** (Render connects to GitHub):
   - Create a GitHub account if you don't have one
   - Create a new repository
   - Push your code:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy on Render.com

1. Go to [Render.com](https://render.com) and sign up (use GitHub login)

2. Click **"New +"** → **"Web Service"**

3. Connect your GitHub repository

4. Fill in the settings:

   - **Name**: `streak-extractor` (or any name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Region**: Choose closest to you
   - **Plan**: Free (or paid if you want)

5. Click **"Create Web Service"**

6. Wait for deployment (2-3 minutes)

7. You'll get a URL like: `https://streak-extractor.onrender.com`

## Step 3: Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com)

2. Navigate to **Messaging** → **Settings** → **WhatsApp Sandbox**

3. Find **"When a message comes in"** field

4. Enter your Render URL:

```
https://streak-extractor.onrender.com/whatsapp/webhook
```

5. Make sure **HTTP POST** is selected

6. Click **Save**

## Step 4: Important - Add Credentials

Since you can't push sensitive files to GitHub:

1. **In Render Dashboard**, go to your service

2. Click **"Environment"**

3. Add these environment variables:

   - Don't need to add anything special - your credientials/cred.json file will be handled below

4. **Upload `credientials/cred.json`** via SFTP or add it to `.gitignore` and manually upload

## Step 5: Test

1. Send an image to your WhatsApp number
2. Your Render app will process it
3. Data saves to Google Sheets

## Troubleshooting

- **Check Logs**: In Render dashboard, click "Logs" to see errors
- **Memory Issues**: Use a paid plan if you run out of memory
- **Credentials**: Make sure `credientials/cred.json` is in the right location on Render

## Auto-Deploy

Every time you push to GitHub, Render automatically redeploys!

```bash
git add .
git commit -m "Update code"
git push origin main
```

Your app will redeploy automatically in 1-2 minutes.
