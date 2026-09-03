from enum import Enum

from pydantic import BaseModel, Field


class DistortionType(str, Enum):
    catastrophizing = "catastrophizing"
    overgeneralization = "overgeneralization"
    mind_reading = "mind_reading"
    fortune_telling = "fortune_telling"
    all_or_nothing = "all_or_nothing"
    mental_filter = "mental_filter"
    none = "none"


class Classification(BaseModel):
    distortion: DistortionType
    confidence: float = Field(ge=0, le=1)
    evidence: str | None = None


class ClassificationResponse(BaseModel):
    classifications: list[Classification] = Field(max_length=3)
    message_id: int
