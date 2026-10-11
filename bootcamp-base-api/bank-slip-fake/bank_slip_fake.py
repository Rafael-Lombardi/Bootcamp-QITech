import os
from datetime import date
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel, Field


TOKEN = os.environ.get("BANKSLIP_API_INTERNAL_TOKEN", "default_token")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class PartyData(BaseModel):
    name: str = Field(min_length=1)
    document_number: str = Field(min_length=1)


class BeneficiaryData(PartyData):
    bank_code: int = Field(gt=0)
    branch: int = Field(gt=0)
    account: int = Field(gt=0)


class CreateBankSlipRequest(BaseModel):
    amount: int = Field(gt=0)
    expiration_date: date
    payer_data: PartyData
    beneficiary_data: BeneficiaryData | None = None


class PayBankSlipRequest(BaseModel):
    idempotency_key: str = Field(min_length=1)


bank_slips: dict[str, dict] = {}
payments: dict[str, dict] = {}
payment_lock = Lock()


def require_token(internal_token: str | None) -> None:
    if internal_token != TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid INTERNAL-TOKEN")


def current_bank_slip(bank_slip_key: str) -> dict:
    bank_slip = bank_slips.get(bank_slip_key)
    if bank_slip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank slip not found")
    if bank_slip["status"] == "OPEN" and date.fromisoformat(bank_slip["expiration_date"]) < date.today():
        bank_slip["status"] = "EXPIRED"
    return bank_slip


@app.get("/health_check", status_code=status.HTTP_204_NO_CONTENT)
def health_check() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/bank_slip", status_code=status.HTTP_201_CREATED)
def create_bank_slip(
    payload: CreateBankSlipRequest,
    internal_token: str | None = Header(default=None, alias="INTERNAL-TOKEN"),
):
    require_token(internal_token)
    bank_slip_key = str(uuid4())
    bank_slip = {
        "bank_slip_key": bank_slip_key,
        **payload.model_dump(mode="json"),
        "status": "OPEN",
    }
    bank_slips[bank_slip_key] = bank_slip
    return bank_slip


@app.get("/bank_slip/{bank_slip_key}")
def get_bank_slip(
    bank_slip_key: str,
    internal_token: str | None = Header(default=None, alias="INTERNAL-TOKEN"),
):
    require_token(internal_token)
    return current_bank_slip(bank_slip_key)


@app.post("/bank_slip/{bank_slip_key}/payment")
def pay_bank_slip(
    bank_slip_key: str,
    payload: PayBankSlipRequest,
    internal_token: str | None = Header(default=None, alias="INTERNAL-TOKEN"),
):
    require_token(internal_token)
    with payment_lock:
        bank_slip = current_bank_slip(bank_slip_key)
        previous_payment = payments.get(payload.idempotency_key)

        if previous_payment is not None:
            if previous_payment["bank_slip_key"] != bank_slip_key:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key already used")
            return previous_payment

        if bank_slip["status"] != "OPEN":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Bank slip is {bank_slip['status']}")

        payment = {
            "bank_slip_key": bank_slip_key,
            "external_transaction_id": str(uuid4()),
            "status": "SETTLED",
        }
        payments[payload.idempotency_key] = payment
        bank_slip["status"] = "PAID"
        bank_slip["external_transaction_id"] = payment["external_transaction_id"]
        return payment
