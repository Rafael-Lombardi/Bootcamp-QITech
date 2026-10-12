from fastapi import Header, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import BankSlipController
from utils.schema_handler import SchemaHandler


class BankSlipResource:
    @SchemaHandler.validate("post_bank_slip.json")
    def on_post(
        self,
        payload: dict,
        chave_de_idempotencia: str = Header(..., alias="chave_de_idempotencia"),
    ) -> JSONResponse:
        bank_slip, was_created = BankSlipController().issue(payload, chave_de_idempotencia)
        response_status = http_status.HTTP_201_CREATED if was_created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(bank_slip), status_code=response_status)

    @SchemaHandler.validate("post_bank_slip_payment.json")
    def on_post_payment(
        self,
        bank_slip_key: str,
        payload: dict,
        chave_de_idempotencia: str = Header(..., alias="chave_de_idempotencia"),
    ) -> JSONResponse:
        transaction, was_created = BankSlipController().pay(
            bank_slip_key,
            payload,
            chave_de_idempotencia,
        )
        response_status = http_status.HTTP_201_CREATED if was_created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(transaction), status_code=response_status)
