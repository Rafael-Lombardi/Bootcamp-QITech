from errors.base_error import QIException


class ClientNotFound(QIException):
    code = "QIT001001"

    def __init__(self, client_key: str) -> None:
        super().__init__(
            "Client not found",
            self.code,
            404,
            f"Client with key {client_key} was not found.",
            "Cliente não encontrado.",
        )


class InvalidClientDocument(QIException):
    code = "QIT001002"

    def __init__(self, document_number: str) -> None:
        super().__init__(
            "Invalid document",
            self.code,
            422,
            f"Document {document_number} has invalid check digits.",
            "O documento informado é inválido.",
        )


class ClientDataConflict(QIException):
    code = "QIT001003"

    def __init__(self, document_number: str) -> None:
        super().__init__(
            "Client data conflict",
            self.code,
            409,
            f"Document {document_number} is already registered with different data.",
            "Documento já cadastrado com dados diferentes.",
        )


class UnderageClient(QIException):
    code = "QIT001004"

    def __init__(self, minimum_age: int) -> None:
        super().__init__(
            "Client is underage",
            self.code,
            422,
            f"Client must be at least {minimum_age} years old.",
            f"É preciso ter pelo menos {minimum_age} anos.",
        )
