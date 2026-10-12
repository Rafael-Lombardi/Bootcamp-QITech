from fastapi import Request, status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import AccountController
from utils.schema_handler import SchemaHandler


class AccountResource:
    @SchemaHandler.validate("post_account.json")
    def on_post(self, client_key: str, payload: dict) -> JSONResponse:
        account, was_created = AccountController().create(client_key, payload)
        response_status = http_status.HTTP_201_CREATED if was_created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(account), status_code=response_status)

    def on_get_by_key(self, account_key: str) -> JSONResponse:
        account = AccountController().get_by_key(account_key)
        return JSONResponse(content=jsonable_encoder(account), status_code=http_status.HTTP_200_OK)

    @SchemaHandler.validate_query_params("get_account_transactions.json")
    def on_get_transactions(self, account_key: str, request: Request) -> JSONResponse:
        limit = int(request.query_params.get("limite", 20))
        cursor = request.query_params.get("proxima")
        statement = AccountController().get_statement(account_key, limit, cursor)
        return JSONResponse(content=jsonable_encoder(statement), status_code=http_status.HTTP_200_OK)

    @SchemaHandler.validate("patch_account.json")
    def on_patch(self, account_key: str, payload: dict) -> JSONResponse:
        account = AccountController().update_status(account_key, payload)
        return JSONResponse(content=jsonable_encoder(account), status_code=http_status.HTTP_200_OK)
