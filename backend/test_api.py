import asyncio
from app.config import get_settings
from google import genai
from google.genai import types

async def test_api():
    settings = get_settings()
    client = genai.Client(api_key=settings.google_api_key)
    try:
        print("Sending test request to Gemini...")
        response = await client.aio.models.generate_content(
            model=settings.gemini_llm_model,
            contents="Say hello!",
        )
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())
