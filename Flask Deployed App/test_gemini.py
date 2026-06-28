
import os
from dotenv import load_dotenv
from google import genai

print("🚀 Script started")

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print("API KEY:", api_key)

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say hello"
)   

print("✅ Response:", response.text)