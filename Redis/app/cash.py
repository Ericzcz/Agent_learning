import hashlib
import json
from typing import Optional

def make_cache_key(
        question: str, 
        model: str = 'gpt-4.0'
    ) -> str:
    
    normalized = question.strip().lower()
    hashed = hashlib.sha256(normalized.encode()).hexdigest()
    
    return f"cache:{hashed}:{model}:"


async def get_cache(
        redis_client, 
        question: str,
    ) -> Optional[dict]:
    
    key = make_cache_key(question)
    cached = await redis_client.get(key)

    if cached is None:
        return None

    try: 
        return json.loads(cached)
    except json.JSONDecodeError as e:
        return None

async def set_cache(
        redis_client, 
        question: str, 
        model: str, 
        data: dict, 
        ttl: int = 3600
    ) -> None:
    
    key = make_cache_key(question, model)
    await redis_client.set(
        key,
        json.dumps(data, ensure_ascii=False),
        ex=ttl
    )

async def delete_cache(
        redis_client, 
        question: str, 
        model: str
    ) -> bool:

    key = make_cache_key(question, model)
    deleted = await redis_client.delete(key)

    return bool(deleted)