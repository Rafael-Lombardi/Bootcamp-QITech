from uuid import uuid4

from tests.integration.client.test_client import request
from tests.integration.transaction.test_transaction import (
    activate_accounts,
    create_account,
    create_client,
    transfer,
)
from tests.utils import DbUtils


class TestStatement:
    def test_returns_transactions_newest_first_with_cursor_pagination(self):
        DbUtils.rollback()
        sender_key = create_account(create_client(40, "StatementSender"), 40)
        recipient_key = create_account(create_client(41, "StatementRecipient"), 41)
        activate_accounts(sender_key, recipient_key)

        _, oldest = transfer(sender_key, 41, 100)
        _, newest = transfer(recipient_key, 40, 50)

        status, first_page = request(
            "GET",
            f"/conta/{sender_key}/transacao?limite=1",
        )
        assert status == 200
        assert first_page["transacoes"][0]["chave_transacao"] == newest["chave_transacao"]
        assert first_page["transacoes"][0]["movimentacao"] == 50
        assert first_page["proxima"] == newest["chave_transacao"]

        status, second_page = request(
            "GET",
            f"/conta/{sender_key}/transacao?limite=1&proxima={first_page['proxima']}",
        )
        assert status == 200
        assert second_page["transacoes"][0]["chave_transacao"] == oldest["chave_transacao"]
        assert second_page["transacoes"][0]["movimentacao"] == -100
        assert second_page["proxima"] is None

    def test_validates_limit_and_cursor_account(self):
        DbUtils.rollback()
        sender_key = create_account(create_client(42, "StatementSender"), 42)
        recipient_key = create_account(create_client(43, "StatementRecipient"), 43)
        other_sender_key = create_account(create_client(44, "OtherSender"), 44)
        other_recipient_key = create_account(create_client(45, "OtherRecipient"), 45)
        activate_accounts(sender_key, recipient_key, other_sender_key, other_recipient_key)
        _, transaction = transfer(sender_key, 43, 100)
        _, unrelated_transaction = transfer(other_sender_key, 45, 100)

        for limit in (0, 101):
            status, response = request("GET", f"/conta/{sender_key}/transacao?limite={limit}")
            assert status == 400
            assert response["code"] == "QIT000001"

        status, response = request(
            "GET",
            f"/conta/{sender_key}/transacao?proxima={uuid4()}",
        )
        assert status == 400
        assert response["code"] == "QIT001030"

        status, response = request(
            "GET",
            f"/conta/{sender_key}/transacao?proxima={unrelated_transaction['chave_transacao']}",
        )
        assert status == 400
        assert response["code"] == "QIT001030"

        status, response = request(
            "GET",
            f"/conta/{sender_key}/transacao?proxima={transaction['chave_transacao']}",
        )
        assert status == 200
        assert response["transacoes"] == []
