from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
import redis.asyncio as redis

from app.cash import make_cache_key, get_cache, set_cache

from app.schemas import AskRequest, AskResponse, IndexRequest, TaskResponse

from app.agent import fake_llm

from app.celery_app import celery_app

from app.tasks import index_document


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis(
        host="localhost",
        port=6383,
        decode_responses=True,
        db=2
    )

    yield

    await app.state.redis.aclose()


app = FastAPI(lifespan=lifespan)




@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest, request: Request):
    redis_client = request.app.state.redis

    cached = await get_cache(redis_client, req.question, req.model)

    if cached is not None:
        return {
            "source": "cache",
            **cached,
        }

    answer = await fake_llm(req.question, req.model)

    data = {
        "answer": answer,
    }

    await set_cache(redis_client, req.question, req.model, data)

    return {
        "source": "agent",
        **data
    }

@app.get("/cache")
async def check_cache(question: str, request: Request):
    r = request.app.state.redis
    key = make_cache_key(question)
    cached = await get_cache(r, question)
    return {
        "key": key,
        "hit": cached is not None,
        "data": cached
    }


@app.delete("/cache")
async def delete_cache(question: str, model: str, request: Request):
    r = request.app.state.redis
    key = make_cache_key(question, model)
    deleted = await delete_cache(r, question)

    return {
        "key": key,
        "deleted": bool(deleted)
    }

@app.post("/index")
def create_index_task(req: IndexRequest):
    task = index_document.delay(req.filename)
    return {
        "task_id": task.id,
        "status": "indexing_submitted",
    }

@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    task = celery_app.AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "status": task.status,
        "result": None,
        "progress": None,
    }

    if task.status == "PROGRESS":
        response["progress"] = task.info
    elif task.ready():
        response["result"] = task.result
    return response