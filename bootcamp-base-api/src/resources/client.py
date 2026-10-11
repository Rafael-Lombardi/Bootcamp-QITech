from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import ClientController
from utils.schema_handler import SchemaHandler


class ClientResource:
    @SchemaHandler.validate("post_client.json")
    def on_post(self, payload: dict) -> JSONResponse:
        client, was_created = ClientController().create(payload)
        response_status = http_status.HTTP_201_CREATED if was_created else http_status.HTTP_200_OK
        return JSONResponse(content=jsonable_encoder(client), status_code=response_status)

    def on_get_by_key(self, client_key: str) -> JSONResponse:
        client = ClientController().get_by_key(client_key)
        return JSONResponse(content=jsonable_encoder(client), status_code=http_status.HTTP_200_OK)
