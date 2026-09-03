import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.llm import classify
from app.models import RequestLog
from app.pricing import cost_usd
from app.schemas import Classification

logger = logging.getLogger("mindbridge")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="MindBridge AI", lifespan=lifespan)


class ClassifyRequest(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/classify")
def classify_text(request: ClassifyRequest, db: Session = Depends(get_db)) -> Classification:
    start = time.perf_counter()
    result, usage = classify(request.text)
    latency_ms = (time.perf_counter() - start) * 1000

    cost = cost_usd(usage["model"], usage["input_tokens"], usage["output_tokens"])

    db.add(
        RequestLog(
            endpoint="/classify",
            model=usage["model"],
            latency_ms=latency_ms,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cost_usd=cost,
        )
    )
    db.commit()

    logger.info(
        json.dumps(
            {
                "endpoint": "/classify",
                "model": usage["model"],
                "latency_ms": latency_ms,
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "cost_usd": cost,
            }
        )
    )

    return result
