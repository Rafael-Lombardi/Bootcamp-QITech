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


class ExternalRecipientNotFound(QIException):
    code = "QIT001015"

    def __init__(self, bank_id: int, branch: int, number: int) -> None:
        super().__init__(
            "External recipient not found",
            self.code,
            404,
            f"External recipient account {bank_id}/{branch}/{number} was not found.",
            "Conta destinatária externa não encontrada.",
        )


class ExternalRecipientNotAvailable(QIException):
    code = "QIT001018"

    def __init__(self, bank_id: int, branch: int, number: int) -> None:
        super().__init__(
            "External recipient not available",
            self.code,
            409,
            f"External recipient account {bank_id}/{branch}/{number} is not active.",
            "Conta destinatária externa não está disponível.",
        )


class ExternalTransactionRejected(QIException):
    code = "QIT001019"

    def __init__(self) -> None:
        super().__init__(
            "External transaction rejected",
            self.code,
            422,
            "The external bank rejected the transaction.",
            "O banco externo rejeitou a transação.",
        )


class ExternalBankTimeout(QIException):
    code = "QIT001020"

    def __init__(self) -> None:
        super().__init__(
            "External bank timeout",
            self.code,
            504,
            "The external bank did not respond before the timeout.",
            "O banco externo não respondeu dentro do prazo.",
        )


class BankSlipNotFound(QIException):
    code = "QIT001024"

    def __init__(self, bank_slip_key: str) -> None:
        super().__init__(
            "Bank slip not found",
            self.code,
            404,
            f"Bank slip {bank_slip_key} was not found.",
            "Boleto não encontrado.",
        )


class BankSlipExpired(QIException):
    code = "QIT001025"

    def __init__(self) -> None:
        super().__init__(
            "Bank slip expired",
            self.code,
            409,
            "The bank slip is expired.",
            "O boleto está vencido.",
        )


class BankSlipAlreadyPaid(QIException):
    code = "QIT001026"

    def __init__(self) -> None:
        super().__init__(
            "Bank slip already paid",
            self.code,
            409,
            "The bank slip has already been paid.",
            "O boleto já foi pago.",
        )


class BankSlipPaymentConflict(QIException):
    code = "QIT001027"

    def __init__(self) -> None:
        super().__init__(
            "Bank slip payment conflict",
            self.code,
            409,
            "The bank slip already has a payment in progress for another payer or amount.",
            "O boleto já possui um pagamento incompatível em andamento.",
        )


class BankSlipTimeout(QIException):
    code = "QIT001028"

    def __init__(self) -> None:
        super().__init__(
            "Bank slip service timeout",
            self.code,
            504,
            "The bank slip service did not respond before the timeout.",
            "O serviço de boletos não respondeu dentro do prazo.",
        )


class BankSlipRejected(QIException):
    code = "QIT001029"

    def __init__(self) -> None:
        super().__init__(
            "Bank slip operation rejected",
            self.code,
            422,
            "The bank slip service rejected the operation.",
            "O serviço de boletos rejeitou a operação.",
        )


class BankSlipBeneficiaryMismatch(QIException):
    code = "QIT001030"

    def __init__(self) -> None:
        super().__init__(
            "Bank slip beneficiary mismatch",
            self.code,
            409,
            "The bank slip beneficiary does not match the locally registered beneficiary.",
            "O beneficiário do boleto não corresponde ao beneficiário local registrado.",
        )
