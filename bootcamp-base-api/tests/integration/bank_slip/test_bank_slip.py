from uuid import uuid4

from sqlalchemy import create_engine, text

from tests.integration.transaction.test_transaction import (
    activate_accounts,
    create_account,
    create_client,
)
from tests.integration.client.test_client import request
from tests.utils import DbUtils


def issue(beneficiary_key: str, amount: int = 700, idempotency_key: str = None):
    return request(
        "POST",
        "/boleto",
        {
            "beneficiario": beneficiary_key,
            "valor": amount,
            "data_vencimento": "2099-12-31",
            "pagador": {"nome": "Fixture Payer", "documento": "52998224725"},
        },
        headers={"chave_de_idempotencia": idempotency_key or str(uuid4())},
    )


def pay(bank_slip_key: str, payer_key: str, idempotency_key: str = None):
    return request(
        "POST",
        f"/boleto/{bank_slip_key}/pagamento",
        {"pagador": payer_key},
        headers={"chave_de_idempotencia": idempotency_key or str(uuid4())},
    )


class TestBankSlip:
    def test_internal_issue_and_payment_credits_exact_beneficiary(self):
        DbUtils.rollback()
        beneficiary_key = create_account(create_client(30, "Beneficiary"), 30)
        payer_key = create_account(create_client(31, "Payer"), 31)
        activate_accounts(beneficiary_key, payer_key)
        issue_key = str(uuid4())

        status, bank_slip = issue(beneficiary_key, idempotency_key=issue_key)
        assert status == 201
        assert bank_slip["estado"] == "REGISTRADO"

        status, repeated_issue = issue(beneficiary_key, idempotency_key=issue_key)
        assert status == 200
        assert repeated_issue == bank_slip

        payment_key = str(uuid4())
        status, transaction = pay(bank_slip["chave_boleto"], payer_key, payment_key)
        assert status == 201
        assert transaction["estado"] == "CONCLUIDA"
        assert transaction["tarifa_cobrada"] == 0
        assert request("GET", f"/conta/{payer_key}")[1]["saldo"] == "13.00"
        assert request("GET", f"/conta/{beneficiary_key}")[1]["saldo"] == "27.00"

        engine = create_engine(DbUtils.database_url())
        with engine.connect() as connection:
            movements = connection.execute(
                text("SELECT movement_cents FROM account_entry ORDER BY id")
            ).scalars().all()
        assert movements == [-700, 700]

    def test_external_fixture_payment_has_no_local_beneficiary_credit(self):
        DbUtils.rollback()
        payer_key = create_account(create_client(32, "ExternalPayer"), 32)
        activate_accounts(payer_key)

        status, transaction = pay("fixture-external-open", payer_key)

        assert status == 201
        assert transaction["estado"] == "CONCLUIDA"
        assert request("GET", f"/conta/{payer_key}")[1]["saldo"] == "10.00"

        engine = create_engine(DbUtils.database_url())
        with engine.connect() as connection:
            movements = connection.execute(text("SELECT movement_cents FROM account_entry")).scalars().all()
            external_id = connection.execute(
                text("SELECT external_transaction_id FROM bank_transaction")
            ).scalar_one()
        assert movements == [-1000]
        assert external_id

    def test_same_boleto_cannot_be_paid_with_a_new_key(self):
        DbUtils.rollback()
        beneficiary_key = create_account(create_client(33, "PaidBeneficiary"), 33)
        payer_key = create_account(create_client(34, "PaidPayer"), 34)
        activate_accounts(beneficiary_key, payer_key)
        _, bank_slip = issue(beneficiary_key, amount=600)

        status, _ = pay(bank_slip["chave_boleto"], payer_key)
        assert status == 201

        status, response = pay(bank_slip["chave_boleto"], payer_key)
        assert status == 409
        assert response["code"] == "QIT001026"

    def test_expired_and_already_paid_fixtures_are_rejected(self):
        DbUtils.rollback()
        payer_key = create_account(create_client(35, "InvalidPayer"), 35)
        activate_accounts(payer_key)

        status, response = pay("fixture-expired", payer_key)
        assert status == 409
        assert response["code"] == "QIT001025"

        status, response = pay("fixture-paid", payer_key)
        assert status == 409
        assert response["code"] == "QIT001026"

    def test_timeout_keeps_payment_pending_and_retry_reconciles(self):
        DbUtils.rollback()
        payer_key = create_account(create_client(36, "TimeoutPayer"), 36)
        activate_accounts(payer_key)
        payment_key = str(uuid4())

        status, response = pay("fixture-external-timeout", payer_key, payment_key)
        assert status == 504
        assert response["code"] == "QIT001028"

        status, transaction = pay("fixture-external-timeout", payer_key, payment_key)
        assert status == 200
        assert transaction["estado"] == "CONCLUIDA"
        assert request("GET", f"/conta/{payer_key}")[1]["saldo"] == "12.50"
