import re
from os import environ
import os
from Script import script
import logging

logger = logging.getLogger(__name__)

def is_enabled(type, value):
    data = environ.get(type, str(value))
    if data.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif data.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        logger.error(f'{type} is invalid, exiting now')
        exit()

def is_valid_ip(ip):
    ip_pattern = r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    return re.match(ip_pattern, ip) is not None

# Bot information
API_ID = environ.get('API_ID', '29124838')
if len(API_ID) == 0:
    logger.error('API_ID is missing, exiting now')
    exit()
else:
    API_ID = int(API_ID)
API_HASH = environ.get('API_HASH', 'd1a293f6fc4c87f59a665f0a68cd607b')
if len(API_HASH) == 0:
    logger.error('API_HASH is missing, exiting now')
    exit()
BOT_TOKEN = environ.get('BOT_TOKEN', '')
if len(BOT_TOKEN) == 0:
    logger.error('BOT_TOKEN is missing, exiting now')
    exit()
BOT_ID = BOT_TOKEN.split(":")[0]
PORT = int(environ.get('PORT', '80'))

# Upload your images to "postimages.org" and get direct link
PICS = (environ.get('PICS', 'https://i.postimg.cc/8C15CQ5y/1.png https://i.postimg.cc/gcNtrv0m/2.png https://i.postimg.cc/cHD71BBz/3.png https://i.postimg.cc/F1XYhY8q/4.png https://i.postimg.cc/1tNwGVxC/5.png https://i.postimg.cc/dtW30QpL/6.png https://i.postimg.cc/139dvs3c/7.png https://i.postimg.cc/QtXVtB8K/8.png https://i.postimg.cc/y8j8G1XV/9.png https://i.postimg.cc/zDF6KyJX/10.png https://i.postimg.cc/fyycVqzd/11.png https://i.postimg.cc/26ZBtBZr/13.png https://i.postimg.cc/PJn8nrWZ/14.png https://i.postimg.cc/cC7txyhz/15.png https://i.postimg.cc/kX9tjGXP/16.png https://i.postimg.cc/zXjH4NVb/17.png https://i.postimg.cc/sggGrLhn/18.png https://i.postimg.cc/y8pgYTh7/19.png')).split()

# Bot Admins
ADMINS = environ.get('ADMINS', '7436687322')
if len(ADMINS) == 0:
    logger.error('ADMINS is missing, exiting now')
    exit()
else:
    ADMINS = [int(admins) for admins in ADMINS.split()]

# Channels
INDEX_CHANNELS = [int(index_channels) if index_channels.startswith("-") else index_channels for index_channels in environ.get('INDEX_CHANNELS', '').split()]
if len(INDEX_CHANNELS) == 0:
    logger.info('INDEX_CHANNELS is empty')
LOG_CHANNEL = environ.get('LOG_CHANNEL', '-1002552925944')
if len(LOG_CHANNEL) == 0:
    logger.error('LOG_CHANNEL is missing, exiting now')
    exit()
else:
    LOG_CHANNEL = int(LOG_CHANNEL)
UPDATES_SEND_CHANNEL = environ.get('UPDATES_SEND_CHANNEL', '-1002520793005')
if len(UPDATES_SEND_CHANNEL) == 0:
    logger.info('UPDATES_SEND_CHANNEL is missing')
    UPDATES_SEND_CHANNEL = None
else:
    UPDATES_SEND_CHANNEL = int(UPDATES_SEND_CHANNEL)

REQUESTS_CHANNEL = environ.get('REQUESTS_CHANNEL', '-1002520793005')
if len(REQUESTS_CHANNEL) == 0:
    logger.info('REQUESTS_CHANNEL is missing, using LOG_CHANNEL')
    REQUESTS_CHANNEL = LOG_CHANNEL
else:
    REQUESTS_CHANNEL = int(REQUESTS_CHANNEL)

# support group
SUPPORT_GROUP = environ.get('SUPPORT_GROUP', 'https://t.me/Your_Movie_Link_8')
if len(SUPPORT_GROUP) == 0:
    SUPPORT_GROUP = None
    logger.warning('SUPPORT_GROUP is missing')
else:
    SUPPORT_GROUP = int(SUPPORT_GROUP)

# MongoDB information
DATA_DATABASE_URL = environ.get('DATA_DATABASE_URL', "mongodb+srv://Fakrudin:fakrudin91056289hay@cluster0.5ilhogs.mongodb.net/?appName=Cluster0")
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'Files') 
FILES_DATABASE_URL = environ.get('FILES_DATABASE_URL', "ongodb+srv://Sukwendar:Sukwendarshing@cluster0.m9fnmdq.mongodb.net/?appName=Cluster0")
SECOND_FILES_DATABASE_URL = environ.get('SECOND_FILES_DATABASE_URL', "mongodb+srv://Karishmajain:Karishmajain@cluster0.df9pten.mongodb.net/?appName=Cluster0")
DATABASE_NAME = environ.get('DATABASE_NAME', "Cluster0")

if len(DATA_DATABASE_URL) == 0 and len(FILES_DATABASE_URL) == 0:
    logger.error('FILES_DATABASE_URL and DATA_DATABASE_URL are missing. You must provide at least one of them. Exiting now.')
    exit()
elif len(DATA_DATABASE_URL) == 0:
    DATA_DATABASE_URL = FILES_DATABASE_URL
    logger.warning('DATA_DATABASE_URL is missing, using FILES_DATABASE_URL as fallback.')
elif len(FILES_DATABASE_URL) == 0:
    FILES_DATABASE_URL = DATA_DATABASE_URL
    logger.warning('FILES_DATABASE_URL is missing, using DATA_DATABASE_URL as fallback.')

if len(SECOND_FILES_DATABASE_URL) == 0:
    logger.info('SECOND_FILES_DATABASE_URL is empty')


# Links
SUPPORT_LINK = environ.get('SUPPORT_LINK', 'https://t.me/movies_updet')
UPDATES_LINK = environ.get('UPDATES_LINK', 'https://t.me/movies_updet')
FILMS_LINK = environ.get('FILMS_LINK', 'https://t.me/Your_Movie_Link_8')
TUTORIAL = environ.get("TUTORIAL", "https://t.me/how_to_downlod09/9")
TUTORIAL_NAME = environ.get("TUTORIAL_NAME", "Tutorial")
VERIFY_TUTORIAL = environ.get("VERIFY_TUTORIAL", "https://t.me/how_to_downlod09/9")

# Bot settings
TIME_ZONE = environ.get('TIME_ZONE', 'Asia/Colombo') # Replace your time zone
DELETE_TIME = int(environ.get('DELETE_TIME', 3600)) # Add time in seconds
CACHE_TIME = int(environ.get('CACHE_TIME', 300))
MAX_BTN = int(environ.get('MAX_BTN', 8))
LANGUAGES = [language.lower() for language in environ.get('LANGUAGES', 'hindi english telugu tamil kannada malayalam marathi punjabi').split()]
QUALITY = [quality.lower() for quality in environ.get('QUALITY', '360p 480p 720p 1080p 2160p').split()]
IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", script.IMDB_TEMPLATE)
FILE_CAPTION = environ.get("FILE_CAPTION", script.FILE_CAPTION)
SHORTLINK_URL = environ.get("SHORTLINK_URL", "Shortxlinks.com")
SHORTLINK_API = environ.get("SHORTLINK_API", "6a3fd84018381fe30f7e1cb2e9a41f92abfb2dd8")
VERIFY_EXPIRE = int(environ.get('VERIFY_EXPIRE', 86400)) # Add time in seconds
WELCOME_TEXT = environ.get("WELCOME_TEXT", script.WELCOME_TEXT)
INDEX_EXTENSIONS = [extensions.lower() for extensions in environ.get('INDEX_EXTENSIONS', 'mp4 mkv').split()]
PM_FILE_DELETE_TIME = int(environ.get('PM_FILE_DELETE_TIME', '3600'))

# boolean settings
USE_CAPTION_FILTER = is_enabled('USE_CAPTION_FILTER', False)
IS_VERIFY = is_enabled('IS_VERIFY', False)
AUTO_DELETE = is_enabled('AUTO_DELETE', False)
WELCOME = is_enabled('WELCOME', False)
PROTECT_CONTENT = is_enabled('PROTECT_CONTENT', False)
LONG_IMDB_DESCRIPTION = is_enabled("LONG_IMDB_DESCRIPTION", False)
LINK_MODE = is_enabled("LINK_MODE", True)
IMDB = is_enabled('IMDB', True)
SPELL_CHECK = is_enabled("SPELL_CHECK", True)
SHORTLINK = is_enabled('SHORTLINK', False)
AUTO_FILTER = is_enabled('AUTO_FILTER', True)
PM_SEARCH = is_enabled('PM_SEARCH', True)

# bot string settings
FORCE_SUB_CHANNELS = environ.get('FORCE_SUB_CHANNELS', '')  # For multiple channels, separate channel IDs with spaces. Example: "-100xxxxx -100xxxxx -100xxxxx"
REQUEST_FORCE_SUB_CHANNEL = environ.get('REQUEST_FORCE_SUB_CHANNEL', 'https://t.me/movies_updet')  # For multiple channels, separate channel IDs with spaces. Example: "-100xxxxx -100xxxxx -100xxxxx"

# for stream
IS_STREAM = is_enabled('IS_STREAM', True)
BIN_CHANNEL = environ.get("BIN_CHANNEL", "https://t.me/movies_updet")
if len(BIN_CHANNEL) == 0:
    logger.error('BIN_CHANNEL is missing, exiting now')
    exit()
else:
    BIN_CHANNEL = int(BIN_CHANNEL)
URL = environ.get("URL", "https://t.me/movies_updet")
if URL:
    if URL.startswith(('https://', 'http://')):
        if not URL.endswith("/"):
            URL += '/'
    elif is_valid_ip(URL):
        URL = f'http://{URL}/'
    else:
        logger.error('URL is not valid, ignoring URL setting')
        URL = ""
else:
    logger.warning("URL is missing. Mini WebApp and Stream features will be disabled.")

#start command reactions 
REACTIONS = [reactions for reactions in environ.get('REACTIONS', '🤝 😇 🤗 😍 👍 🎅 😐 🥰 🤩 😱 🤣 😘 👏 😛 😈 🎉 ⚡️ 🫡 🤓 😎 🏆 🔥 🤭 🌚 🆒 👻 😁').split()]  # Multiple reactions can be used separated by space
EFFECT_IDS = [effect for effect in environ.get('EFFECT_IDS', '5104841245755180586 5104858069142078462 5159385139981059251 5046509860389126442 5046589136895476101 5107584321108051014').split()]

# for Premium 
IS_PREMIUM = is_enabled('IS_PREMIUM', True)
OWNER_USERNAME = environ.get("OWNER_USERNAME", "ABHISHEK_KUMAR")
PAYMENT_QR_CODE = "https://files.catbox.moe/zdqcba.jpg" # add your payment qr code link, like upi qr code or any crypto qr code link
PAYMENT_ID = "mypayment@id"  # add your payment id like upi id or crypto address

# Format -- Days: ['CURRENCY', Price]
PREMIUM_PLANS = {
    7: ['USD', 1], 
    14: ['USD', 2],
    30: ['USD', 3],
    365: ['USD', 10]
}
PAYMENT_TYPE = "UPI"  # can be changed to "Crypto (TRC20)" or "PayPal" or etc....


# for TMDb
TMDB_API_KEY = environ.get("TMDB_API_KEY", "")  # Get API key from here - https://www.themoviedb.org/settings/api
if len(TMDB_API_KEY) == 0:
    logger.info('TMDB_API_KEY is missing')
    TMDB_API_KEY = None
