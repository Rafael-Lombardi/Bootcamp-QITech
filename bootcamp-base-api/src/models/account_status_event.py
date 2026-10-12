from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from models.account_status import AccountStatus
from models.base import Base


class AccountStatusEvent(Base):
    __tablename__ = "account_status_event"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)
    status = Column(
        Enum(
            AccountStatus,
            name="account_event_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
    )
    reason = Column(String(255), nullable=False)
    event_datetime = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    account = relationship("Account", back_populates="status_events")
