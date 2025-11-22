import os
from dotenv import load_dotenv
load_dotenv()

# Bot token
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Channel IDs
EMBED_CHANNEL_ID = int(os.getenv("EMBED_CHANNEL_ID"))
POSTING_CHANNEL_ID = int(os.getenv("POSTING_CHANNEL_ID"))
MODERATOR_CHANNEL_ID = int(os.getenv("MODERATOR_CHANNEL_ID"))

# File paths
PERSISTENCE_FILE = os.getenv("PERSISTENCE_FILE")
ARCHIVE_FILE = os.getenv("ARCHIVE_FILE")

# Logging configuration
LOG_FILE = os.getenv("LOG_FILE")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")