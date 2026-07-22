import uuid
from datetime import timedelta

from app.models.base import utcnow
from app.models.enums import ShipmentStatus

# Linear status progression used by the "advance shipment" endpoint and the
# public tracking timeline. A real carrier integration would replace this.
SHIPMENT_FLOW = [
    ShipmentStatus.PREPARING,
    ShipmentStatus.IN_TRANSIT,
    ShipmentStatus.DELIVERED,
]

_STATUS_LABELS = {
    ShipmentStatus.PREPARING: "Pedido em preparação",
    ShipmentStatus.IN_TRANSIT: "A caminho",
    ShipmentStatus.DELIVERED: "Entregue",
}


def generate_tracking_code() -> str:
    return f"BR{uuid.uuid4().hex[:10].upper()}"


def default_estimated_delivery():
    return utcnow() + timedelta(days=5)


def next_status(current: ShipmentStatus) -> ShipmentStatus | None:
    idx = SHIPMENT_FLOW.index(current)
    if idx + 1 < len(SHIPMENT_FLOW):
        return SHIPMENT_FLOW[idx + 1]
    return None


def status_label(status: ShipmentStatus) -> str:
    return _STATUS_LABELS[status]
