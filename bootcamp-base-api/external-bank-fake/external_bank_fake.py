import asyncio
import os
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel, Field


TOKEN = os.environ.get("EXTERNAL_BANK_TOKEN", "default_token")
DELAY_SECONDS = float(os.environ.get("EXTERNAL_BANK_DELAY_SECONDS", "2"))

app = FastAPI(title="External Bank Fake", docs_url=None, redoc_url=None, openapi_url=None)


class Account(BaseModel):
    bank_code: int = Field(gt=0)
    branch: int = Field(gt=0)
    number: int = Field(gt=0)


class TransactionRequest(BaseModel):
    external_transaction_id: str = Field(min_length=1)
    amount: int = Field(gt=0)
    channel: Literal["PIX", "TED"]
    sender: Account
    recipient: Account


class AdminTransactionRequest(TransactionRequest):
    status: Literal["SETTLED", "REJECTED"] = "SETTLED"


transactions: dict[str, dict] = {}
attempts: dict[str, int] = {}


def require_token(internal_token: str | None) -> None:
    if internal_token != TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid INTERNAL-TOKEN")


def account_suffix(number: int) -> str:
    return str(number).zfill(4)[-4:]


def transaction_body(payload: TransactionRequest, transaction_status: str) -> dict:
    return {**payload.model_dump(), "status": transaction_status}


@app.get("/health_check", status_code=status.HTTP_204_NO_CONTENT)
def health_check() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/accounts/{bank_code}/{branch}/{number}")
async def get_account(
    bank_code: int,
    branch: int,
    number: int,
    internal_token: str | None = Header(default=None, alias="INTERNAL-TOKEN"),
):
    require_token(internal_token)
    suffix = account_suffix(number)

    if suffix == "5555":
        await asyncio.sleep(DELAY_SECONDS)
    if suffix == "0000":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    account_status = "BLOCKED" if suffix == "6666" else "ACTIVE"
    return {
        "bank_code": bank_code,
        "branch": branch,
        "number": number,
        "status": account_status,
    }


@app.post("/transactions", status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionRequest,
    internal_token: str | None = Header(default=None, alias="INTERNAL-TOKEN"),
):
    require_token(internal_token)
    transaction_id = payload.external_transaction_id
    suffix = account_suffix(payload.recipient.number)
    attempts[transaction_id] = attempts.get(transaction_id, 0) + 1

    if transaction_id not in transactions:
        external_status = "REJECTED" if suffix == "9999" else "SETTLED"
        transactions[transaction_id] = transaction_body(payload, external_status)

    if suffix == "8888" or (suffix == "7777" and attempts[transaction_id] == 1):
        await asyncio.sleep(DELAY_SECONDS)

    return transactions[transaction_id]


@app.get("/transactions/{external_transaction_id}")
async def get_transaction(
    external_transaction_id: str,
    internal_token: str | None = Header(default=None, alias="INTERNAL-TOKEN"),
):
    require_token(internal_token)
    transaction = transactions.get(external_transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


@app.post("/admin/transactions", status_code=status.HTTP_201_CREATED)
async def create_admin_transaction(
    payload: AdminTransactionRequest,
    internal_token: str | None = Header(default=None, alias="INTERNAL-TOKEN"),
):
    require_token(internal_token)
    transaction_id = payload.external_transaction_id
    existing = transactions.get(transaction_id)
    if existing is not None:
        return existing

    transaction = transaction_body(payload, payload.status)
    transactions[transaction_id] = transaction
    return transaction
