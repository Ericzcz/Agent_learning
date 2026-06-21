import time
from app.celery_app import celery_app

@celery_app.task(bind=True)
def index_document(self, filename: str):

    steps = [
        "loading document",
        "splitting chunks",
        "creating embeddings",
        "saving to vector database",
    ]

    total = len(steps)

    for i, step in enumerate(steps, start=1):
        self.update_state(
            state="PROGRESS",
            meta={
                "current_step": step,
                "current": i,
                "total": total,
            },
        )
        time.sleep(3)

    return {
        "filename": filename,
        "status": "indexed",
        "chunks": 128,
    }