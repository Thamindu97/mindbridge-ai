from fastapi import FastAPI
from pydantic import BaseModel

from app.llm import classify
from app.schemas import Classification

app = FastAPI(title="MindBridge AI")


class ClassifyRequest(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/classify")
def classify_text(request: ClassifyRequest) -> Classification:
    return classify(request.text)
