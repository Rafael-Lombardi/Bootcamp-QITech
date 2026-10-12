from datetime import date
from uuid import uuid4

from sqlalchemy import create_engine, text

from tests.integration.client.test_client import request
from tests.utils import DbUtils
from tests.utils.random_generator import RandomGenerator


def create_client() -> str:
    payload = {
        "documento": RandomGenerator.generate_cpf().replace(".", "").replace("-", ""),
        "nome": "Cliente Conta",
        "nascimento": date(1990, 1, 1).isoformat(),
    }
    status, response = request("POST", "/cliente", payload)
    assert status == 201
    return response["chave_cliente"]


class TestAccount:
    def test_creates_gets_and_lists_account_on_client(self):
        DbUtils.rollback()
        client_key = create_client()
        payload = {"agencia": 1234, "numero": 5678}

        status, created = request("POST", f"/cliente/{client_key}/conta", payload)
        assert status == 201

        status, account = request("GET", f"/conta/{created['chave_conta']}")
        assert status == 200
        assert account["banco_id"] == 1
        assert account["agencia"] == payload["agencia"]
        assert account["numero"] == payload["numero"]
        assert account["estado"] == "PENDENTE"
        assert account["saldo"] == "0.00"

        status, client = request("GET", f"/cliente/{client_key}")
        assert status == 200
        assert client["contas"] == [account]

    def test_reuses_account_for_same_client_and_rejects_other_client(self):
        DbUtils.rollback()
        first_client = create_client()
        second_client = create_client()
        payload = {"agencia": 1234, "numero": 5678}

        first_status, first = request("POST", f"/cliente/{first_client}/conta", payload)
        repeat_status, repeat = request("POST", f"/cliente/{first_client}/conta", payload)
        other_status, other = request("POST", f"/cliente/{second_client}/conta", payload)

        assert first_status == 201
        assert repeat_status == 200
        assert repeat == first
        assert other_status == 409
        assert other["code"] == "QIT001006"

    def test_limits_client_to_five_open_accounts(self):
        DbUtils.rollback()
        client_key = create_client()

        for number in range(1, 6):
            status, _ = request(
                "POST",
                f"/cliente/{client_key}/conta",
                {"agencia": 1234, "numero": number},
            )
            assert status == 201

        status, response = request(
            "POST",
            f"/cliente/{client_key}/conta",
            {"agencia": 1234, "numero": 6},
        )
        assert status == 409
        assert response["code"] == "QIT001007"

    def test_deactivates_account_with_zero_balance(self):
        DbUtils.rollback()
        account_key = self._create_account()

        status, account = request(
            "PATCH",
            f"/conta/{account_key}",
            {"novo_estado": "DESATIVADA", "razao": "Encerramento solicitado"},
        )

        assert status == 200
        assert account["estado"] == "DESATIVADA"
        assert account["saldo"] == "0.00"

    def test_rejects_deactivation_with_non_zero_balance(self):
        DbUtils.rollback()
        account_key = self._create_account()
        engine = create_engine(DbUtils.database_url())
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE account SET balance_cents = 1 WHERE account_key = :key"),
                {"key": account_key},
            )

        status, response = request(
            "PATCH",
            f"/conta/{account_key}",
            {"novo_estado": "DESATIVADA", "razao": "Encerramento solicitado"},
        )

        assert status == 409
        assert response["code"] == "QIT001009"

    def test_rejects_deactivation_with_in_progress_transaction(self):
        DbUtils.rollback()
        account_key = self._create_account()
        engine = create_engine(DbUtils.database_url())
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO bank_transaction(
                        transaction_key, idempotency_key,
                        sender_bank_id, sender_branch, sender_number,
                        recipient_bank_id, recipient_branch, recipient_number,
                        amount_cents, fee_cents, channel, status
                    ) VALUES (
                        :transaction_key, :idempotency_key,
                        1, 1234, 5678,
                        2, 4321, 8765,
                        100, 0, 'PIX', 'EM_ANDAMENTO'
                    )
                    """
                ),
                {"transaction_key": str(uuid4()), "idempotency_key": str(uuid4())},
            )

        status, response = request(
            "PATCH",
            f"/conta/{account_key}",
            {"novo_estado": "DESATIVADA", "razao": "Encerramento solicitado"},
        )

        assert status == 409
        assert response["code"] == "QIT001010"

    def test_rejects_deactivation_for_unknown_account(self):
        DbUtils.rollback()

        status, response = request(
            "PATCH",
            f"/conta/{uuid4()}",
            {"novo_estado": "DESATIVADA", "razao": "Encerramento solicitado"},
        )

        assert status == 404
        assert response["code"] == "QIT001005"

    @staticmethod
    def _create_account() -> str:
        client_key = create_client()
        status, response = request(
            "POST",
            f"/cliente/{client_key}/conta",
            {"agencia": 1234, "numero": 5678},
        )
        assert status == 201
        return response["chave_conta"]
