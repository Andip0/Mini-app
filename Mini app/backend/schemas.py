from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator


class JobRequest(BaseModel):

    numbers: List[float] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of numbers to process (1–50 items).",
        examples=[[1, 2, 3, 4, 5]],
    )
    operation: Literal["square", "cube", "factorial"] = Field(
        default="square",
        description="Mathematical operation to apply to each number in parallel.",
    )

    @field_validator("numbers")
    @classmethod
    def no_negative_for_factorial(cls, v, info):
        op = info.data.get("operation", "square")
        if op == "factorial":
            for n in v:
                if n < 0 or n != int(n):
                    raise ValueError(
                        "Factorial requires non-negative integers."
                    )
                if n > 20:
                    raise ValueError(
                        "Factorial inputs must be ≤ 20 to avoid overflow."
                    )
        return v


class JobSubmittedResponse(BaseModel):

    job_id: str = Field(..., description="Celery task / chord ID to poll with.")
    total_tasks: int = Field(..., description="Number of parallel sub-tasks spawned.")
    message: str = Field(default="Job accepted and queued.")


class TaskResult(BaseModel):

    input: float
    output: float
    operation: str


class JobStatusResponse(BaseModel):

    job_id: str
    status: str = Field(
        ...,
        description="pending | started | success | failed | <other celery state>",
    )
    results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Per-number results (only present when status == 'success').",
    )
    summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Aggregate stats (only present when status == 'success').",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message (only present when status == 'failed').",
    )
