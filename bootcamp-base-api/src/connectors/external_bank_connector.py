from connectors.rest_connector import BaseConnectorResponse, RestConnector
from constants import (
    EXTERNAL_BANK_API_INTERNAL_TOKEN,
    EXTERNAL_BANK_API_TIMEOUT,
    EXTERNAL_BANK_API_URL,
)


class ExternalBankConnector(RestConnector):
    def __init__(self) -> None:
        super().__init__(
            class_name=__name__,
            base_url=EXTERNAL_BANK_API_URL,
            timeout=EXTERNAL_BANK_API_TIMEOUT,
            internal_token=EXTERNAL_BANK_API_INTERNAL_TOKEN,
        )

    def get_account(self, bank_id: int, branch: int, number: int) -> BaseConnectorResponse:
        return self.send(
            endpoint=f"/accounts/{bank_id}/{branch}/{number}",
            method="GET",
        )

    def create_transaction(
        self,
        external_transaction_id: str,
        amount: int,
        channel: str,
        sender: dict,
        recipient: dict,
    ) -> BaseConnectorResponse:
        return self.send(
            endpoint="/transactions",
            method="POST",
            payload={
                "external_transaction_id": external_transaction_id,
                "amount": amount,
                "channel": channel,
                "sender": self._external_account(sender),
                "recipient": self._external_account(recipient),
            },
        )

    def get_transaction(self, external_transaction_id: str) -> BaseConnectorResponse:
        return self.send(
            endpoint=f"/transactions/{external_transaction_id}",
            method="GET",
        )

    @staticmethod
    def _external_account(account: dict) -> dict:
        return {
            "bank_code": account["bank_id"],
            "branch": account["branch"],
            "number": account["number"],
        }
