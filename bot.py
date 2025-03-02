import os
import discord
import requests
from discord.ext import commands
from notion_client import Client
from flask import Flask, request, redirect

# Load environment variables
NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Flask web server for OAuth callback
app = Flask(__name__)

@app.route("/")
def home():
    return "DSGN Dock is running!"

# Step 1: Redirect user to Notion OAuth page
@app.route("/login")
def login():
    notion_auth_url = (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={NOTION_CLIENT_ID}"
        f"&response_type=code"
        f"&owner=user"
        f"&redirect_uri={NOTION_REDIRECT_URI}"
    )
    return redirect(notion_auth_url)

# Step 2: Handle Notion OAuth callback
@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Authorization failed", 400

    # Exchange authorization code for access token
    token_url = "https://api.notion.com/v1/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": NOTION_REDIRECT_URI,
        "client_id": NOTION_CLIENT_ID,
        "client_secret": NOTION_CLIENT_SECRET
    }
    response = requests.post(token_url, data=payload)
    data = response.json()

    access_token = data.get("access_token")
    if not access_token:
        return "Failed to retrieve access token", 400

    return f"Authorization successful! Your Notion access token: {access_token}"

# Function to save a URL to Notion using OAuth access token
def add_to_notion(url, access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    notion_database_id = os.getenv("NOTION_DATABASE_ID")
    data = {
        "parent": {"database_id": notion_database_id},
        "properties": {
            "URL": {"title": [{"text": {"content": url}}]}
        }
    }
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
    return response.json()

# Discord command to save a URL
@bot.command()
async def save(ctx, url: str):
    await ctx.send("🔄 Processing...")

    # Temporary access token (OAuth flow required)
    access_token = "your-temporary-access-token"  # Replace with actual OAuth flow retrieval

    result = add_to_notion(url, access_token)
    if "id" in result:
        await ctx.send(f"✅ Saved to Notion: {url}")
    else:
        await ctx.send(f"❌ Failed to save: {result}")

# Run both Flask and Discord bot
if __name__ == "__main__":
    import threading
    def run_flask():
        app.run(host="0.0.0.0", port=3000)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    bot.run(DISCORD_BOT_TOKEN)
