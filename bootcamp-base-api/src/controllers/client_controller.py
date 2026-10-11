from datetime import date

from sqlalchemy.exc import IntegrityError

from controllers.base_controller import BaseController
from dtos import ClientDTO
from errors import ClientDataConflict, ClientNotFound, InvalidClientDocument, InvalidSchema, UnderageClient
from models import Client, ClientType
from repositories import ClientRepository
from utils.document_number import is_valid_cnpj, is_valid_cpf


MINIMUM_AGE = 18


class ClientController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)

    def create(self, client_data: dict) -> tuple[dict, bool]:
        document_number = client_data["documento"]
        client_type = ClientType.PF if len(document_number) == 11 else ClientType.PJ

        self._validate_document(document_number, client_type)
        if client_type == ClientType.PF:
            self._validate_age(client_data["nascimento"])

        existing_client = self.client_repository.get_by_document_number(document_number)
        if existing_client is not None:
            return self._existing_client_response(existing_client, client_data)

        client = self.client_repository.create(client_data, client_type)
        try:
            self.session.flush()
            client_dto = ClientDTO.only_key(client)
            self.session.commit()
            return client_dto, True
        except IntegrityError:
            self.session.rollback()
            existing_client = self.client_repository.get_by_document_number(document_number)
            return self._existing_client_response(existing_client, client_data)

    def get_by_key(self, client_key: str) -> dict:
        client = self.client_repository.get_by_key(client_key)
        if client is None:
            raise ClientNotFound(client_key)
        return ClientDTO.obj_to_dict(client)

    def _existing_client_response(self, client: Client, client_data: dict) -> tuple[dict, bool]:
        if client is None or not self._has_same_data(client, client_data):
            raise ClientDataConflict(client_data["documento"])
        return ClientDTO.only_key(client), False

    @staticmethod
    def _has_same_data(client: Client, client_data: dict) -> bool:
        return (
            client.name == client_data["nome"]
            and client.corporate_name == client_data.get("razao_social")
            and (
                client.birthdate.isoformat() if client.birthdate is not None else None
            ) == client_data.get("nascimento")
        )

    @staticmethod
    def _validate_document(document_number: str, client_type: ClientType) -> None:
        is_valid = is_valid_cpf(document_number) if client_type == ClientType.PF else is_valid_cnpj(document_number)
        if not is_valid:
            raise InvalidClientDocument(document_number)

    @staticmethod
    def _validate_age(raw_birthdate: str) -> None:
        try:
            birthdate = date.fromisoformat(raw_birthdate)
        except ValueError:
            raise InvalidSchema(f"'{raw_birthdate}' is not a real date")

        today = date.today()
        age = today.year - birthdate.year
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age -= 1
        if age < MINIMUM_AGE:
            raise UnderageClient(MINIMUM_AGE)
