import asyncio
from app.ai.llm import LLMService

async def test_llm():
    try:
        service = LLMService()
        print("Sending request to LLMService...")
        result = await service.generate_json("Say hello world in valid JSON format like {\"greeting\": \"hello world\"}")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error testing LLM: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
