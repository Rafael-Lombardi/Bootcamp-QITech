from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.account_status import AccountStatus
from models.base import Base


class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True)
    account_key = Column(String(36), nullable=False)
    bank_id = Column(Integer, nullable=False)
    branch = Column(Integer, nullable=False)
    number = Column(Integer, nullable=False)
    client_id = Column(Integer, ForeignKey("client.id"), nullable=False)
    balance_cents = Column(BigInteger, nullable=False, server_default="0")
    status = Column(
        Enum(
            AccountStatus,
            name="account_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        server_default=AccountStatus.PENDENTE.value,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("account_key"),
        UniqueConstraint("bank_id", "branch", "number"),
    )

    client = relationship("Client", back_populates="accounts")
    status_events = relationship("AccountStatusEvent", back_populates="account")
