# Docker Run Guide

This image packages the `code.ipynb` workflow as a FastAPI service.

## Build

```bash
docker build -t rag-notebook .
```

## Run

Use your local `.env` file so API keys are injected at runtime instead of baked into the image.

```bash
docker run --rm -it \
  -p 8000:8000 \
  --env-file .env \
  -v "$(pwd)":/app/RAG \
  rag-notebook
```

Then open:

```text
http://localhost:8000/docs
```

## Notes

- The API exposes `GET /health` and `POST /chat`.
- `code.ipynb` logic reads knowledge files from `llm-universe/data_base/knowledge_db`.
- The Chroma vector store will be created under `llm-universe/data_base/vector_db/chroma`.
- The volume mount keeps source edits and generated vector data on your host machine.
