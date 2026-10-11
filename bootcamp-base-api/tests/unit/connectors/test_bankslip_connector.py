from unittest.mock import patch

from connectors.bankslip_connector import BankSlipConnector


def test_pay_bank_slip_sends_idempotent_payment_request():
    connector = BankSlipConnector()

    with patch.object(connector, "send") as send:
        connector.pay_bank_slip("slip-123", "transaction-456")

    send.assert_called_once_with(
        endpoint="/bank_slip/slip-123/payment",
        method="POST",
        payload={"idempotency_key": "transaction-456"},
    )
