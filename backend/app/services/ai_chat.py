import uuid

from sqlmodel import Session, select

from app.core.config import settings
from app.models.chat import ChatMessage
from app.models.enums import ChatRole
from app.models.order import Order, OrderItem
from app.models.shipment import Shipment
from app.services.shipping import status_label

# Number of prior turns fed back to the model for continuity.
_HISTORY_TURNS = 10


def _build_order_context(session: Session, order_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """Assemble REAL order/shipment facts the model may reference.

    The model is told to answer only from this context and never invent order
    data — so everything it can say about an order comes from here.
    """
    order = session.get(Order, order_id)
    if order is None or order.buyer_id != user_id:
        return "Nenhum pedido válido foi associado a esta conversa."

    items = session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    shipment = session.exec(select(Shipment).where(Shipment.order_id == order.id)).first()

    lines = [
        f"Pedido: {order.id}",
        f"Status do pedido: {order.status.value}",
        f"Status do pagamento: {order.payment_status.value}",
        f"Total: R$ {order.total_cents / 100:.2f}",
        "Itens:",
    ]
    for it in items:
        lines.append(
            f"  - {it.title_snapshot} x{it.quantity} " f"(R$ {it.unit_price_cents / 100:.2f} cada)"
        )
    if shipment:
        lines.append(f"Envio: {status_label(shipment.status)} ({shipment.status.value})")
        lines.append(f"Código de rastreio: {shipment.tracking_code}")
        if shipment.estimated_delivery:
            lines.append(f"Previsão de entrega: {shipment.estimated_delivery:%d/%m/%Y}")
    return "\n".join(lines)


def _system_prompt(order_context: str) -> str:
    return (
        "Você é o assistente de atendimento de um marketplace online. "
        "Responda em português, de forma cordial e objetiva. "
        "Você ajuda o comprador com dúvidas sobre status do pedido, prazo de "
        "entrega e a política de devolução simplificada (devoluções são aceitas "
        "em até 7 dias após a entrega). "
        "Use SOMENTE os dados de pedido fornecidos abaixo — nunca invente números "
        "de pedido, códigos de rastreio, prazos ou valores. "
        "Se a pergunta exigir informação que você não tem, diga que vai encaminhar "
        "para um atendente humano.\n\n"
        f"=== DADOS DO PEDIDO (fonte de verdade) ===\n{order_context}\n"
    )


def generate_reply(
    session: Session,
    *,
    user_id: uuid.UUID,
    message: str,
    order_id: uuid.UUID | None,
) -> str:
    """Produce the assistant reply, grounded in real backend context.

    Degrades gracefully: without an ANTHROPIC_API_KEY configured (e.g. the demo
    runs without a key) it returns a helpful canned response instead of failing,
    so the chat flow is always demonstrable.
    """
    order_context = (
        _build_order_context(session, order_id, user_id)
        if order_id
        else "Nenhum pedido foi associado a esta conversa."
    )

    if not settings.anthropic_api_key:
        return (
            "Olá! No momento o atendimento por IA está em modo de demonstração "
            "(sem chave da API configurada). "
            + (
                "Aqui estão os dados do seu pedido:\n" + order_context
                if order_id
                else "Assim que uma chave for configurada, poderei responder suas dúvidas."
            )
        )

    # Load recent history so the conversation has continuity.
    history = session.exec(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(_HISTORY_TURNS)
    ).all()
    history = list(reversed(history))

    anthropic_messages = [
        {"role": "user" if m.role == ChatRole.USER else "assistant", "content": m.content}
        for m in history
    ]
    anthropic_messages.append({"role": "user", "content": message})

    # Imported lazily so the app still boots if the SDK/key is absent.
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=_system_prompt(order_context),
        messages=anthropic_messages,
    )
    return "".join(block.text for block in response.content if block.type == "text")
