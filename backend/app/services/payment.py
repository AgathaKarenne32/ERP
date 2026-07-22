import time
import uuid
from dataclasses import dataclass


@dataclass
class ChargeResult:
    success: bool
    transaction_id: str
    provider: str


class PaymentService:
    """Payment gateway abstraction.

    This mock approves every charge after a short delay. The interface
    (`charge`) is deliberately provider-agnostic so a real gateway
    (Mercado Pago, Stripe) can be dropped in later by implementing the same
    method — see ROADMAP.md. Amounts are always integer cents.
    """

    provider = "mock"

    def charge(self, *, amount_cents: int, currency: str, buyer_id: uuid.UUID) -> ChargeResult:
        # Simulate a synchronous gateway round-trip (~1s) that always approves.
        time.sleep(1)
        return ChargeResult(
            success=True,
            transaction_id=f"mock_{uuid.uuid4().hex[:16]}",
            provider=self.provider,
        )


payment_service = PaymentService()
