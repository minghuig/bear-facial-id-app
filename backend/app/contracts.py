from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
class BodyDetection(Contract):
    category: int = Field(gt=0)
    confidence: float = Field(ge=0, le=1)
    bbox: list[float]
class BodyDetectionResult(Contract):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    detections: list[BodyDetection]
class HeadDetectionResult(Contract):
    body_index: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    boxes: list[list[float]]
class HeadResult(Contract):
    observation_id: str
    embedding: list[float] | None = None
    diagnostics: dict = Field(default_factory=dict)
    error: str | None = None
class Result(Contract):
    token: str
    pipeline: str
    provenance: dict
    body_detection: BodyDetectionResult | None = None
    head_detections: list[HeadDetectionResult] = Field(default_factory=list)
    heads: list[HeadResult] = Field(default_factory=list)
    error: str | None = None
class Claim(Contract):
    stage: Literal['body_detection', 'head_detection', 'recognition']
    pipeline: str
class Lease(Contract):
    token: str
class ReviewInput(Contract):
    state: Literal['confirmed', 'unresolved', 'ignored', 'unusable']
    bear_id: str | None = None
class CropReviewInput(Contract):
    state: Literal['accepted', 'rejected']
class MatchInput(Contract):
    reference_id: str
    expected_bear_id: str | None
    expected_review_state: Literal['confirmed', 'unresolved', 'ignored', 'unusable']
    expected_reference_bear_id: str | None
class UndoMatchInput(Contract):
    head_review_id: str
    reference_review_id: str | None
class BearInput(Contract):
    name: str | None = Field(default=None, max_length=120)
