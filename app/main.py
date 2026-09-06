import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import Base, engine, get_db
from app.llm import classify
from app.models import Classification as ClassificationModel
from app.models import Conversation, Message, RequestLog, User
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


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str | None = None


class UserOut(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str | None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    message_id: int
    classification: Classification


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@app.post("/auth/token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(user.id))


@app.get("/auth/me")
def read_current_user(current_user: User = Depends(get_current_user)) -> UserOut:
    return current_user


@app.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, int]:
    conversation = Conversation(user_id=current_user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return {"id": conversation.id}


@app.post("/conversations/{conversation_id}/messages")
def create_message(
    conversation_id: int,
    request: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this conversation")

    message = Message(conversation_id=conversation.id, role="user", content=request.content)
    db.add(message)
    db.commit()
    db.refresh(message)

    try:
        result, usage = classify(request.content)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Classification service temporarily unavailable",
        )

    db.add(
        ClassificationModel(
            message_id=message.id,
            distortion_type=result.distortion.value,
            confidence=result.confidence,
            evidence=result.evidence,
            model_used=usage["model"],
        )
    )
    db.commit()

    return MessageResponse(message_id=message.id, classification=result)


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


@app.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    count, avg_latency_ms, total_cost_usd = db.query(
        func.count(RequestLog.id),
        func.avg(RequestLog.latency_ms),
        func.sum(RequestLog.cost_usd),
    ).one()

    return {
        "count": count,
        "avg_latency_ms": avg_latency_ms,
        "total_cost_usd": total_cost_usd,
    }
