from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from dotenv import find_dotenv, load_dotenv
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_classic.retrievers.contextual_compression import (
    ContextualCompressionRetriever,
)
from langchain_cohere import CohereRerank
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    UnstructuredMarkdownLoader,
)
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

_ = load_dotenv(find_dotenv())

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "llm-universe" / "data_base" / "knowledge_db"
VECTOR_DIR = BASE_DIR / "llm-universe" / "data_base" / "vector_db" / "chroma"


def _iter_knowledge_files(folder_path: Path) -> Iterable[Path]:
    for path in folder_path.rglob("*"):
        if path.is_file():
            yield path


def _load_documents(folder_path: Path) -> list[Document]:
    loaders = []
    for file_path in _iter_knowledge_files(folder_path):
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            loaders.append(PyMuPDFLoader(str(file_path)))
        elif suffix == ".md":
            loaders.append(UnstructuredMarkdownLoader(str(file_path)))

    documents: list[Document] = []
    for loader in loaders:
        documents.extend(loader.load())
    return documents


def _split_documents(documents: list[Document]) -> list[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
    )
    return text_splitter.split_documents(documents)


def _build_or_load_vectordb(split_documents: list[Document]) -> Chroma:
    embedding = OpenAIEmbeddings(model="text-embedding-3-small")
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    vectordb = Chroma(
        persist_directory=str(VECTOR_DIR),
        embedding_function=embedding,
    )

    if not any(VECTOR_DIR.iterdir()):
        batch_size = 50
        for index in range(0, len(split_documents), batch_size):
            batch = split_documents[index : index + batch_size]
            vectordb.add_documents(batch)

    return vectordb


def _combine_documents(documents: list[Document]) -> str:
    return "\n\n".join(document.page_content for document in documents)


@lru_cache(maxsize=1)
def create_rag_chain():
    if not KNOWLEDGE_DIR.exists():
        raise FileNotFoundError(f"Knowledge directory not found: {KNOWLEDGE_DIR}")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required")
    if not os.getenv("COHERE_API_KEY"):
        raise RuntimeError("COHERE_API_KEY is required")

    documents = _load_documents(KNOWLEDGE_DIR)
    split_documents = _split_documents(documents)
    vectordb = _build_or_load_vectordb(split_documents)

    vector_retriever = vectordb.as_retriever(search_kwargs={"k": 10})

    bm25_retriever = BM25Retriever.from_documents(split_documents)
    bm25_retriever.k = 10

    hybrid_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25_retriever],
        weights=[0.5, 0.5],
    )

    reranker = CohereRerank(
        model="rerank-v3.5",
        top_n=8,
    )

    retriever = ContextualCompressionRetriever(
        base_retriever=hybrid_retriever,
        base_compressor=reranker,
    )

    llm = ChatOpenAI(
        model="gpt-5.1",
        temperature=0,
    )

    condense_question_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "请根据聊天记录和用户最新问题，把用户最新问题改写成一个可以独立理解的问题。不要回答问题，只需要返回改写后的问题。",
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ]
    )

    retriever_docs = RunnableBranch(
        (
            lambda payload: not payload.get("chat_history", False),
            RunnableLambda(lambda payload: payload["input"]) | retriever,
        ),
        condense_question_prompt | llm | StrOutputParser() | retriever,
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个问答任务的助手。请使用检索到的上下文片段回答问题。如果你不知道答案就说不知道。\n\n{context}",
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ]
    )

    qa_chain = (
        RunnablePassthrough.assign(
            context=lambda payload: _combine_documents(payload["context"])
        )
        | qa_prompt
        | llm
        | StrOutputParser()
    )

    return RunnablePassthrough.assign(
        context=retriever_docs,
    ).assign(
        answer=qa_chain,
    )
