import asyncio

async def fake_llm(question: str, model: str = 'gpt-4.0') -> str:
    await asyncio.sleep(2)
    return f"这是 {model} 对「{question}」的回答"