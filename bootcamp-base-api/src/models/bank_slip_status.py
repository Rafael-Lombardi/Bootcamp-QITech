from enum import Enum


class BankSlipStatus(str, Enum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    REGISTRADO = "REGISTRADO"
    FALHOU = "FALHOU"
