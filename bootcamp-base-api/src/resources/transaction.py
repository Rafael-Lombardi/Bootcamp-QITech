from fastapi import Header, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import TransactionController
from utils.schema_handler import SchemaHandler


class TransactionResource:
    @SchemaHandler.validate("post_transaction.json")
    def on_post(
        self,
        payload: dict,
        chave_de_idempotencia: str = Header(..., alias="chave_de_idempotencia"),
    ) -> JSONResponse:
        transaction, was_created = TransactionController().create(payload, chave_de_idempotencia)
        response_status = http_status.HTTP_201_CREATED if was_created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(transaction), status_code=response_status)
