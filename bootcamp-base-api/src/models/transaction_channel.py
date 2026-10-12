from enum import Enum


class TransactionChannel(str, Enum):
    PIX = "PIX"
    TED = "TED"
