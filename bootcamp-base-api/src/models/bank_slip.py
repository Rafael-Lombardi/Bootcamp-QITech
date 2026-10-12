from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from models.bank_slip_status import BankSlipStatus
from models.base import Base


class BankSlip(Base):
    __tablename__ = "bank_slip"

    id = Column(Integer, primary_key=True)
    bank_slip_key = Column(String(255), nullable=True)
    issuance_idempotency_key = Column(String(36), nullable=False)
    beneficiary_account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    expiration_date = Column(Date, nullable=False)
    payer_name = Column(String(255), nullable=False)
    payer_document_number = Column(String(14), nullable=False)
    status = Column(
        Enum(
            BankSlipStatus,
            name="bank_slip_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("bank_slip_key"),
        UniqueConstraint("issuance_idempotency_key"),
    )
