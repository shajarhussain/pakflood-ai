from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services import chat_service

router = APIRouter()


class ChatMessage(BaseModel):
    role: str          # "user" or "model"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Send a message to the PakFlood AI assistant.

    The service automatically detects intent (flood events / zones / weather /
    district-specific) and fetches only the relevant DB context before calling
    Gemini, minimising token usage.
    """
    history = [{"role": m.role, "content": m.content} for m in req.history]
    reply = await chat_service.generate_reply(req.message, history)
    return ChatResponse(reply=reply)
