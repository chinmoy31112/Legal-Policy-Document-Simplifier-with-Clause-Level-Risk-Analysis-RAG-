import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

models_to_test = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-3.5-flash"]

for m in models_to_test:
    try:
        res = client.models.generate_content(model=m, contents="hello")
        print(f"SUCCESS: {m}")
        break
    except Exception as e:
        print(f"FAILED {m}: {e}")
