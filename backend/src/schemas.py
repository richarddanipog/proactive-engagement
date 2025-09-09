from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any

PageType = Literal["home", "collection", "product", "cart", "checkout"]
EventType = Literal["page_view", "click", "cart_update", "dwell_tick"]


class Event(BaseModel):
    type: EventType
    page: PageType
    meta: Dict[str, Any] = Field(default_factory=dict)
    timestamp: int  # in milliseconds


class SessionSnapshot(BaseModel):
    events: List[Event]
    current_page: PageType
    cart_items: int = 0
    time_on_site: int = 0  # in seconds


class DecisionRequest(BaseModel):
    session: SessionSnapshot


class DecisionResponse(BaseModel):
    should_show: bool
    message: Optional[str] = None
    ttl_seconds: int = 0
