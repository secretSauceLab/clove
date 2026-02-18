import os
from dotenv import load_dotenv

load_dotenv()  # loads .env locally if present

API_KEY = os.getenv("API_KEY", "")