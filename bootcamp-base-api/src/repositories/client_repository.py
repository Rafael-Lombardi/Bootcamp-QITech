from datetime import date
from uuid import uuid4

from database import Context
from models import Client, ClientType


class ClientRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, client_data: dict, client_type: ClientType) -> Client:
        client = Client(
            client_key=str(uuid4()),
            client_type=client_type,
            document_number=client_data["documento"],
            name=client_data["nome"],
            corporate_name=client_data.get("razao_social"),
            birthdate=date.fromisoformat(client_data["nascimento"]) if client_type == ClientType.PF else None,
        )
        self.session.add(client)
        return client

    def get_by_key(self, client_key: str) -> Client:
        return self.session.query(Client).filter(Client.client_key == client_key).first()

    def get_by_document_number(self, document_number: str) -> Client:
        return self.session.query(Client).filter(Client.document_number == document_number).first()
