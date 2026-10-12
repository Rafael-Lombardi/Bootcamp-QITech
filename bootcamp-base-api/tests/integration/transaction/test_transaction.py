from datetime import date
from uuid import uuid4

from sqlalchemy import create_engine, text

from tests.integration.client.test_client import request
from tests.utils import DbUtils
from tests.utils.random_generator import RandomGenerator


def create_client(seed: int, name: str) -> str:
    payload = {
        "documento": RandomGenerator.generate_cpf().replace(".", "").replace("-", ""),
        "nome": f"{name}-{seed}",
        "nascimento": date(1990, 1, 1).isoformat(),
    }
    status, response = request("POST", "/cliente", payload)
    assert status == 201
    return response["chave_cliente"]


def create_account(client_key: str, number: int) -> str:
    status, response = request(
        "POST",
        f"/cliente/{client_key}/conta",
        {"agencia": 1234, "numero": number},
    )
    assert status == 201
    return response["chave_conta"]


def activate_accounts(*account_keys: str) -> None:
    engine = create_engine(DbUtils.database_url())
    with engine.begin() as connection:
        for account_key in account_keys:
            connection.execute(
                text("UPDATE account SET status = 'ATIVA', balance_cents = 2000 WHERE account_key = :key"),
                {"key": account_key},
            )


class TestTransaction:
    def test_internal_pix_creates_signed_entries_and_moves_balances(self):
        DbUtils.rollback()
        sender_client = create_client(1, "Sender")
        recipient_client = create_client(2, "Recipient")
        sender_key = create_account(sender_client, 1)
        recipient_key = create_account(recipient_client, 2)
        activate_accounts(sender_key, recipient_key)

        payload = {
            "remetente": sender_key,
            "destinatario": {"banco_id": 1, "agencia": 1234, "conta": 2},
            "valor": 1000,
            "canal": "PIX",
        }
        idempotency_key = str(uuid4())
        status, response = request(
            "POST",
            "/transacao",
            payload,
            headers={"chave_de_idempotencia": idempotency_key},
        )

        assert status == 201
        assert response["estado"] == "CONCLUIDA"
        assert response["valor"] == 1000
        assert response["tarifa_cobrada"] == 0

        status, repeated = request(
            "POST",
            "/transacao",
            payload,
            headers={"chave_de_idempotencia": idempotency_key},
        )
        assert status == 200
        assert repeated == response

        status, sender = request("GET", f"/conta/{sender_key}")
        assert status == 200
        assert sender["saldo"] == "10.00"

        status, recipient = request("GET", f"/conta/{recipient_key}")
        assert status == 200
        assert recipient["saldo"] == "30.00"

        engine = create_engine(DbUtils.database_url())
        with engine.connect() as connection:
            movements = connection.execute(text("SELECT movement_cents FROM account_entry ORDER BY id")).scalars().all()
        assert movements == [-1000, 1000]

    def test_internal_ted_charges_sender_fee(self):
        DbUtils.rollback()
        sender_key = create_account(create_client(3, "Sender"), 3)
        recipient_key = create_account(create_client(4, "Recipient"), 4)
        activate_accounts(sender_key, recipient_key)

        status, response = request(
            "POST",
            "/transacao",
            {
                "remetente": sender_key,
                "destinatario": {"banco_id": 1, "agencia": 1234, "conta": 4},
                "valor": 1000,
                "canal": "TED",
            },
            headers={"chave_de_idempotencia": str(uuid4())},
        )

        assert status == 201
        assert response["tarifa_cobrada"] == 1000
        assert request("GET", f"/conta/{sender_key}")[1]["saldo"] == "0.00"
        assert request("GET", f"/conta/{recipient_key}")[1]["saldo"] == "30.00"
