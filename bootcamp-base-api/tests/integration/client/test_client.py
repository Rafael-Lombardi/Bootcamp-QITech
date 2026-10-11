from datetime import date
from os import environ
from uuid import uuid4

import requests

from tests.utils import DbUtils


BASE_URL = (
    f"http://{environ.get('SERVER_LOCALHOST', '0.0.0.0')}"
    f":{environ.get('API_PORT', '3000')}"
)
HEADERS = {"INTERNAL-TOKEN": environ.get("INTERNAL_TOKEN", "default_token")}


def request(method: str, path: str, payload: dict = None):
    response = requests.request(method, f"{BASE_URL}{path}", json=payload, headers=HEADERS)
    return response.status_code, response.json()


def adult_birthdate() -> str:
    today = date.today()
    return date(today.year - 18, today.month, min(today.day, 28)).isoformat()


class TestClient:
    def test_rejects_body_outside_schema(self):
        status, response = request("POST", "/cliente", {"documento": "52998224725"})

        assert status == 400
        assert response["code"] == "QIT000001"

    def test_rejects_invalid_cpf_and_cnpj_check_digits(self):
        payloads = [
            {
                "documento": "11111111111",
                "nome": "Pessoa Inválida",
                "nascimento": adult_birthdate(),
            },
            {
                "documento": "11222333000182",
                "nome": "Empresa Inválida",
                "razao_social": "Empresa Inválida LTDA",
            },
        ]

        for payload in payloads:
            status, response = request("POST", "/cliente", payload)
            assert status == 422
            assert response["code"] == "QIT001002"

    def test_rejects_underage_individual_client(self):
        today = date.today()
        birthdate = date(today.year - 17, today.month, min(today.day, 28)).isoformat()
        payload = {
            "documento": "52998224725",
            "nome": "Pessoa Menor",
            "nascimento": birthdate,
        }

        status, response = request("POST", "/cliente", payload)

        assert status == 422
        assert response["code"] == "QIT001004"

    def test_returns_not_found_for_unknown_client(self):
        status, response = request("GET", f"/cliente/{uuid4()}")

        assert status == 404
        assert response["code"] == "QIT001001"

    def test_creates_and_gets_individual_client(self):
        DbUtils.rollback()
        payload = {
            "documento": "52998224725",
            "nome": "Maria da Silva",
            "nascimento": adult_birthdate(),
        }

        status, created = request("POST", "/cliente", payload)
        assert status == 201

        status, client = request("GET", f"/cliente/{created['chave_cliente']}")
        assert status == 200
        assert client["documento"] == payload["documento"]
        assert client["tipo"] == "PF"
        assert client["contas"] == []

    def test_repeated_equal_data_is_idempotent_but_different_data_conflicts(self):
        DbUtils.rollback()
        payload = {
            "documento": "11222333000181",
            "nome": "Empresa Exemplo",
            "razao_social": "Empresa Exemplo LTDA",
        }

        first_status, first = request("POST", "/cliente", payload)
        second_status, second = request("POST", "/cliente", payload)
        conflict_status, conflict = request("POST", "/cliente", {**payload, "nome": "Outro Nome"})

        assert first_status == 201
        assert second_status == 200
        assert first == second
        assert conflict_status == 409
        assert conflict["code"] == "QIT001003"

    def test_rejects_unicode_digits(self):
        payload = {
            "documento": "٥٢٩٩٨٢٢٤٧٢٥",
            "nome": "Pessoa Inválida",
            "nascimento": adult_birthdate(),
        }

        status, response = request("POST", "/cliente", payload)

        assert status == 400
        assert response["code"] == "QIT000001"
