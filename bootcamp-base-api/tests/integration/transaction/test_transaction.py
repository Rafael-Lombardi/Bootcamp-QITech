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


def transfer(sender_key: str, recipient_number: int, amount: int, channel: str = "PIX", idempotency_key: str = None):
    return request(
        "POST",
        "/transacao",
        {
            "remetente": sender_key,
            "destinatario": {"banco_id": 1, "agencia": 1234, "conta": recipient_number},
            "valor": amount,
            "canal": channel,
        },
        headers={"chave_de_idempotencia": idempotency_key or str(uuid4())},
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
            endpoints = connection.execute(
                text(
                    """
                    SELECT sender_bank_id, sender_branch, sender_number,
                           recipient_bank_id, recipient_branch, recipient_number
                    FROM bank_transaction
                    """
                )
            ).one()
        assert movements == [-1000, 1000]
        assert endpoints == (1, 1234, 1, 1, 1234, 2)

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

    def test_rejects_unknown_sender(self):
        DbUtils.rollback()

        status, response = transfer(str(uuid4()), 1, 100)

        assert status == 404
        assert response["code"] == "QIT001013"

    def test_rejects_unknown_recipient(self):
        DbUtils.rollback()
        sender_key = create_account(create_client(5, "Sender"), 5)
        activate_accounts(sender_key)

        status, response = transfer(sender_key, 999, 100)

        assert status == 404
        assert response["code"] == "QIT001014"

    def test_rejects_inactive_sender(self):
        DbUtils.rollback()
        sender_key = create_account(create_client(6, "Sender"), 6)
        create_account(create_client(7, "Recipient"), 7)

        status, response = transfer(sender_key, 7, 100)

        assert status == 409
        assert response["code"] == "QIT001016"

    def test_rejects_unavailable_recipient(self):
        DbUtils.rollback()
        sender_key = create_account(create_client(8, "Sender"), 8)
        create_account(create_client(9, "Recipient"), 9)
        activate_accounts(sender_key)

        status, response = transfer(sender_key, 9, 100)

        assert status == 409
        assert response["code"] == "QIT001017"

    def test_rejects_insufficient_balance(self):
        DbUtils.rollback()
        sender_key = create_account(create_client(10, "Sender"), 10)
        recipient_key = create_account(create_client(11, "Recipient"), 11)
        activate_accounts(sender_key, recipient_key)

        status, response = transfer(sender_key, 11, 2001)

        assert status == 422
        assert response["code"] == "QIT001021"

    def test_rejects_same_account_transfer(self):
        DbUtils.rollback()
        sender_key = create_account(create_client(12, "Sender"), 12)
        activate_accounts(sender_key)

        status, response = transfer(sender_key, 12, 100)

        assert status == 422
        assert response["code"] == "QIT001023"

    def test_rejects_idempotency_key_for_different_request(self):
        DbUtils.rollback()
        sender_key = create_account(create_client(13, "Sender"), 13)
        recipient_key = create_account(create_client(14, "Recipient"), 14)
        activate_accounts(sender_key, recipient_key)
        idempotency_key = str(uuid4())

        status, _ = transfer(sender_key, 14, 100, idempotency_key=idempotency_key)
        assert status == 201

        status, response = transfer(sender_key, 14, 200, idempotency_key=idempotency_key)

        assert status == 422
        assert response["code"] == "QIT001022"
