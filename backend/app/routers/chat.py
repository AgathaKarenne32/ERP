from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.chat import ChatMessage
from app.models.enums import ChatRole
from app.models.user import User
from app.schemas.chat import ChatMessageOut, ChatRequest, ChatResponse
from app.services.ai_chat import generate_reply

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatResponse:
    # Persist the user's message, then generate + persist the assistant reply.
    user_msg = ChatMessage(
        user_id=user.id,
        order_id=payload.order_id,
        role=ChatRole.USER,
        content=payload.message,
    )
    session.add(user_msg)
    session.commit()

    reply_text = generate_reply(
        session, user_id=user.id, message=payload.message, order_id=payload.order_id
    )

    assistant_msg = ChatMessage(
        user_id=user.id,
        order_id=payload.order_id,
        role=ChatRole.ASSISTANT,
        content=reply_text,
    )
    session.add(assistant_msg)
    session.commit()
    session.refresh(assistant_msg)
    return ChatResponse(reply=ChatMessageOut(**assistant_msg.model_dump()))


@router.get("/history", response_model=list[ChatMessageOut])
def history(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ChatMessageOut]:
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.asc())
    ).all()
    return [ChatMessageOut(**m.model_dump()) for m in messages]
