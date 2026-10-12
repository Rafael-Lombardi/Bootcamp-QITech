from enum import Enum


class TransactionStatus(str, Enum):
    CONCLUIDA = "CONCLUIDA"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CANCELADA = "CANCELADA"
    FALHOU = "FALHOU"
