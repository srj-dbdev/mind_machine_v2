from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))

print("OpenAI connection initialized successfully")