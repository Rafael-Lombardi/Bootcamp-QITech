from models import Client, ClientType
from dtos.account_dto import AccountDTO


class ClientDTO:
    @staticmethod
    def only_key(client: Client) -> dict:
        return {"chave_cliente": client.client_key}

    @staticmethod
    def obj_to_dict(client: Client) -> dict:
        dto = {
            "chave_cliente": client.client_key,
            "tipo": client.client_type.value,
            "documento": client.document_number,
            "nome": client.name,
            "contas": [AccountDTO.obj_to_dict(account) for account in client.accounts],
        }
        if client.client_type == ClientType.PF:
            dto["nascimento"] = client.birthdate.isoformat()
        else:
            dto["razao_social"] = client.corporate_name
        return dto
