import unittest

from external_bank_fake import (
    Account,
    AdminTransactionRequest,
    TransactionRequest,
    attempts,
    create_admin_transaction,
    create_transaction,
    transactions,
)


class ExternalBankFakeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        transactions.clear()
        attempts.clear()

    async def test_repeated_transaction_is_idempotent(self):
        payload = TransactionRequest(
            external_transaction_id="E123",
            amount=1000,
            channel="PIX",
            sender=Account(bank_code=1, branch=1, number=1234),
            recipient=Account(bank_code=2, branch=2, number=9999),
        )

        first = await create_transaction(payload, "default_token")
        second = await create_transaction(payload, "default_token")

        self.assertEqual(first, second)
        self.assertEqual(first["status"], "REJECTED")
        self.assertEqual(len(transactions), 1)

    async def test_admin_transaction_is_queryable(self):
        payload = AdminTransactionRequest(
            external_transaction_id="E456",
            amount=2000,
            channel="TED",
            sender=Account(bank_code=2, branch=2, number=1234),
            recipient=Account(bank_code=1, branch=1, number=5678),
        )

        result = await create_admin_transaction(payload, "default_token")

        self.assertEqual(result["status"], "SETTLED")
        self.assertEqual(transactions["E456"], result)


if __name__ == "__main__":
    unittest.main()
