import os
import re

from fastapi import FastAPI, Header, HTTPException, Response, status


TOKEN = os.environ.get("DOCUMENT_VALIDATOR_TOKEN", "default_token")

# Documento válido que começa com este prefixo volta com situação irregular.
IRREGULAR_PREFIX = "1234"

app = FastAPI(title="Document Validator Fake", docs_url=None, redoc_url=None, openapi_url=None)


def require_token(internal_token: str | None) -> None:
    if internal_token != TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid INTERNAL-TOKEN")


def check_digit(digits: list[int], weights: list[int]) -> int:
    remainder = sum(digit * weight for digit, weight in zip(digits, weights)) % 11
    return 0 if remainder < 2 else 11 - remainder


def is_valid_cpf(cpf: str) -> bool:
    if not re.fullmatch(r"[0-9]{11}", cpf) or len(set(cpf)) == 1:
        return False

    digits = [int(character) for character in cpf]
    first = check_digit(digits[:9], [10, 9, 8, 7, 6, 5, 4, 3, 2])
    second = check_digit(digits[:10], [11, 10, 9, 8, 7, 6, 5, 4, 3, 2])
    return digits[9:] == [first, second]


def is_valid_cnpj(cnpj: str) -> bool:
    if not re.fullmatch(r"[0-9]{14}", cnpj) or len(set(cnpj)) == 1:
        return False

    digits = [int(character) for character in cnpj]
    first = check_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = check_digit(digits[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digits[12:] == [first, second]


@app.get("/health_check", status_code=status.HTTP_204_NO_CONTENT)
def health_check() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/cpf/{cpf}")
def get_cpf(
    cpf: str,
    internal_token: str | None = Header(default=None, alias="INTERNAL-TOKEN"),
):
    require_token(internal_token)
    if not is_valid_cpf(cpf):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid CPF")

    cpf_status = "SUSPENSA" if cpf.startswith(IRREGULAR_PREFIX) else "REGULAR"
    return {"cpf": cpf, "status": cpf_status}


@app.get("/cnpj/{cnpj}")
def get_cnpj(
    cnpj: str,
    internal_token: str | None = Header(default=None, alias="INTERNAL-TOKEN"),
):
    require_token(internal_token)
    if not is_valid_cnpj(cnpj):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid CNPJ")

    cnpj_status = "INAPTA" if cnpj.startswith(IRREGULAR_PREFIX) else "ATIVA"
    return {"cnpj": cnpj, "status": cnpj_status}
