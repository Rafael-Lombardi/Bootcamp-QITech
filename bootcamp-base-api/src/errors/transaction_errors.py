from errors.base_error import QIException


class SenderAccountNotFound(QIException):
    code = "QIT001013"

    def __init__(self, account_key: str) -> None:
        super().__init__(
            "Sender account not found",
            self.code,
            404,
            f"Sender account with key {account_key} was not found.",
            "Conta remetente não encontrada.",
        )


class RecipientAccountNotFound(QIException):
    code = "QIT001014"

    def __init__(self, bank_id: int, branch: int, number: int) -> None:
        super().__init__(
            "Recipient account not found",
            self.code,
            404,
            f"Recipient account {bank_id}/{branch}/{number} was not found.",
            "Conta destinatária não encontrada.",
        )


class SenderAccountNotActive(QIException):
    code = "QIT001016"

    def __init__(self) -> None:
        super().__init__(
            "Sender account is not active",
            self.code,
            409,
            "Sender account must be ATIVA.",
            "Conta remetente não está ativa.",
        )


class RecipientAccountNotAvailable(QIException):
    code = "QIT001017"

    def __init__(self) -> None:
        super().__init__(
            "Recipient account is not available",
            self.code,
            409,
            "Recipient account must be ATIVA or BLOQUEADA.",
            "Conta destinatária não está disponível.",
        )


class InsufficientBalance(QIException):
    code = "QIT001021"

    def __init__(self) -> None:
        super().__init__(
            "Insufficient balance",
            self.code,
            422,
            "Sender balance is lower than amount plus fee.",
            "Saldo insuficiente para valor e tarifa.",
        )


class IdempotencyKeyConflict(QIException):
    code = "QIT001022"

    def __init__(self) -> None:
        super().__init__(
            "Idempotency key conflict",
            self.code,
            422,
            "Idempotency key was already used for another request.",
            "Chave de idempotência já usada em outra requisição.",
        )


class SameAccountTransfer(QIException):
    code = "QIT001023"

    def __init__(self) -> None:
        super().__init__(
            "Same account transfer",
            self.code,
            422,
            "Sender and recipient accounts must be different.",
            "Remetente e destinatário devem ser contas diferentes.",
        )
