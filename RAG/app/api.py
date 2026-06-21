from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.rag_chain import create_rag_chain

app = FastAPI(
    title="RAG API",
    version="1.0.0",
    description="FastAPI wrapper for the code.ipynb RAG workflow.",
)


class ChatMessage(BaseModel):
    role: Literal["human", "ai"] = Field(..., description="Message speaker role.")
    content: str = Field(..., min_length=1, description="Message content.")


class ChatRequest(BaseModel):
    input: str = Field(..., min_length=1, description="Latest user question.")
    chat_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior turns used for question rewriting.",
    )


class ChatResponse(BaseModel):
    answer: str
    context: list[str]


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        chain = create_rag_chain()
        result = chain.invoke(
            {
                "input": request.input,
                "chat_history": [
                    (message.role, message.content) for message in request.chat_history
                ],
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        answer=result["answer"],
        context=[document.page_content for document in result["context"]],
    )
