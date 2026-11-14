from datetime import datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, Field


class DisputeRequest(BaseModel):
    # Used as the .docx filename, so restrict it to safe characters.
    chargeback_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    merchant_id: str
    transaction_id: str
    amount: float
    reason_code: str
    reason_description: str = ""
    dispute_deadline: str = Field(default_factory=lambda: (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"))


class DisputeResponse(BaseModel):
    chargeback_id: str
    verdict: str
    winability_score: Optional[float]
    strategy_reasoning: Optional[str]
    recommended_arguments: Optional[List[str]]
    review_passed: Optional[bool]
    dispute_category: Optional[str]
    urgency: Optional[str]
    agent_trace: List[str]
    document_path: Optional[str]
    escalation_reason: Optional[str]
