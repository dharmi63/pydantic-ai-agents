from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    user_id: int
    query: str
    session_id: Optional[int] = None