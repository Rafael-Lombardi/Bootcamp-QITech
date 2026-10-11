import unittest
from datetime import date, timedelta

from app import (
    BeneficiaryData,
    CreateBankSlipRequest,
    PartyData,
    PayBankSlipRequest,
    bank_slips,
    create_bank_slip,
    pay_bank_slip,
    payments,
)


class BankSlipFakeTest(unittest.TestCase):
    def setUp(self):
        bank_slips.clear()
        payments.clear()

    def test_payment_is_idempotent_and_keeps_beneficiary(self):
        bank_slip = create_bank_slip(
            CreateBankSlipRequest(
                amount=15000,
                expiration_date=date.today() + timedelta(days=1),
                payer_data=PartyData(name="Pagador", document_number="123"),
                beneficiary_data=BeneficiaryData(
                    name="Beneficiario",
                    document_number="456",
                    bank_code=1,
                    branch=10,
                    account=20,
                ),
            ),
            "default_token",
        )
        payload = PayBankSlipRequest(idempotency_key="idem-1")

        first = pay_bank_slip(bank_slip["bank_slip_key"], payload, "default_token")
        second = pay_bank_slip(bank_slip["bank_slip_key"], payload, "default_token")

        self.assertEqual(first, second)
        self.assertEqual(bank_slip["beneficiary_data"]["account"], 20)
        self.assertEqual(bank_slip["status"], "PAID")


if __name__ == "__main__":
    unittest.main()
