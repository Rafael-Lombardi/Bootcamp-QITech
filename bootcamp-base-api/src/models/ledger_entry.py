from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from models.base import Base


class LedgerEntry(Base):
    __tablename__ = "account_entry"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("bank_transaction.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    movement_cents = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    transaction = relationship("Transaction", back_populates="entries")
