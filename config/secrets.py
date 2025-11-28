# Load from environment variables or .env file
import os
from dotenv import load_dotenv

load_dotenv()

# AI Model API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORG = os.getenv("OPENAI_ORG")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
HUGGING_FACE = os.getenv("HUGGING_FACE")

# Google Drive API Key
GDRIVE_API_KEY = os.getenv("GDRIVE_API_KEY")

# Discord Bot Token
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
