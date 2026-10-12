from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, BigInteger, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.base import Base
from models.transaction_channel import TransactionChannel
from models.transaction_status import TransactionStatus


class Transaction(Base):
    __tablename__ = "bank_transaction"

    id = Column(Integer, primary_key=True)
    transaction_key = Column(String(36), nullable=False)
    idempotency_key = Column(String(36), nullable=False)
    sender_account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    recipient_account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    amount_cents = Column(BigInteger, nullable=False)
    fee_cents = Column(BigInteger, nullable=False, server_default="0")
    channel = Column(
        Enum(
            TransactionChannel,
            name="transaction_channel",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda channels: [channel.value for channel in channels],
        ),
        nullable=False,
    )
    status = Column(
        Enum(
            TransactionStatus,
            name="transaction_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("transaction_key"),
        UniqueConstraint("idempotency_key"),
    )

    sender_account = relationship("Account", foreign_keys=[sender_account_id])
    recipient_account = relationship("Account", foreign_keys=[recipient_account_id])
    entries = relationship("LedgerEntry", back_populates="transaction")
