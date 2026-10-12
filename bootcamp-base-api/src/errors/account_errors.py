from errors.base_error import QIException


class AccountNotFound(QIException):
    code = "QIT001005"

    def __init__(self, account_key: str) -> None:
        super().__init__(
            "Account not found",
            self.code,
            404,
            f"Account with key {account_key} was not found.",
            "Conta não encontrada.",
        )


class AccountOwnedByAnotherClient(QIException):
    code = "QIT001006"

    def __init__(self, branch: int, number: int) -> None:
        super().__init__(
            "Account already registered",
            self.code,
            409,
            f"Account {branch}/{number} belongs to another client.",
            "Agência e conta já pertencem a outro cliente.",
        )


class ClientAccountLimit(QIException):
    code = "QIT001007"

    def __init__(self, maximum: int) -> None:
        super().__init__(
            "Account limit reached",
            self.code,
            409,
            f"Client cannot have more than {maximum} open accounts.",
            f"Cliente não pode ter mais de {maximum} contas abertas.",
        )
