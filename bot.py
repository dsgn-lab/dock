import discord
from discord.ext import commands
import requests
from notion_client import Client
from bs4 import BeautifulSoup

# Load environment variables
import os
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Initialize Notion client
notion = Client(auth=NOTION_API_KEY)

# Define bot with command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Predefined categories
CATEGORIES = ["Tech", "Marketing", "E-commerce", "Design", "Business", "Health"]

# Function to fetch webpage content
def fetch_page_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string if soup.title else "No Title Found"
        paragraphs = soup.find_all("p")
        content = " ".join([p.text for p in paragraphs[:5]])  # First 5 paragraphs
        return title, content
    except Exception as e:
        return "Error fetching page", str(e)

# Function to generate summary and category using DeepSeek
def summarize_and_categorize(title, content):
    prompt = f"""
    Summarize this content in 1-2 sentences:
    Title: {title}
    Content: {content}
    
    Then, suggest a category from: {CATEGORIES}
    Format: "Summary: <summary> | Category: <category>"
    """

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are an AI that summarizes web pages and categorizes them."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    if "choices" in data:
        output = data["choices"][0]["message"]["content"]
        summary, category = output.split("| Category: ")
        return summary.strip(), category.strip()
    else:
        return "Failed to generate summary", "Unknown"

# Function to add data to Notion
def add_to_notion(url, title, summary, category):
    try:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Title": {"title": [{"text": {"content": title}}]},
                "URL": {"url": url},
                "Summary": {"rich_text": [{"text": {"content": summary}}]},
                "Category": {"select": {"name": category}},
            },
        )
        return True
    except Exception as e:
        return str(e)

# Discord command to save a link
@bot.command()
async def save(ctx, url: str):
    await ctx.send("🔄 Processing...")

    # Fetch page content
    title, content = fetch_page_content(url)

    # Generate summary and category
    summary, category = summarize_and_categorize(title, content)

    # Save to Notion
    success = add_to_notion(url, title, summary, category)

    if success == True:
        await ctx.send(f"✅ Saved to Notion!\n**Title:** {title}\n**Summary:** {summary}\n**Category:** {category}")
    else:
        await ctx.send(f"❌ Failed to save to Notion: {success}")

# Run the bot
bot.run(DISCORD_BOT_TOKEN)
