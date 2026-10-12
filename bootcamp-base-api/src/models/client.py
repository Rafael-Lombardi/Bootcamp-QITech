from sqlalchemy import CheckConstraint, Column, Date, DateTime, Enum, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from models.base import Base
from models.client_type import ClientType


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True)
    client_key = Column(String(36), nullable=False)
    client_type = Column(
        Enum(
            ClientType,
            name="client_type",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda client_types: [client_type.value for client_type in client_types],
        ),
        nullable=False,
    )
    document_number = Column(String(14), nullable=False)
    name = Column(String(255), nullable=False)
    corporate_name = Column(String(255))
    birthdate = Column(Date)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("client_key"),
        UniqueConstraint("document_number"),
        CheckConstraint("client_type IN ('PF', 'PJ')"),
        CheckConstraint(
            "(client_type = 'PF' AND birthdate IS NOT NULL AND corporate_name IS NULL) OR "
            "(client_type = 'PJ' AND birthdate IS NULL AND corporate_name IS NOT NULL)"
        ),
    )

    accounts = relationship("Account", back_populates="client", lazy="selectin")
