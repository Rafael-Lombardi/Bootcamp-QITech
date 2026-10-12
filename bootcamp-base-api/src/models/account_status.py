from enum import Enum


class AccountStatus(str, Enum):
    PENDENTE = "PENDENTE"
    ATIVA = "ATIVA"
    BLOQUEADA = "BLOQUEADA"
    DESATIVADA = "DESATIVADA"
