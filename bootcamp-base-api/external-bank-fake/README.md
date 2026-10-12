# External Bank Fake

Mock do banco externo usado pela API nas transferências PIX e TED.

O estado fica somente em memória. Reiniciar o serviço restaura o mock vazio.

## Autenticação

Todas as rotas, exceto `GET /health_check`, exigem:

```http
INTERNAL-TOKEN: default_token
```

O valor é configurado por `EXTERNAL_BANK_TOKEN` no serviço do mock. A API
envia esse valor por `EXTERNAL_BANK_API_INTERNAL_TOKEN`.

## Endpoints

### `GET /accounts/{bank_code}/{branch}/{number}`

Consulta uma conta externa.

O número da conta controla os cenários do mock:

| Sufixo | Resposta | Uso |
|---|---|---|
| `0000` | `404` | conta inexistente |
| `5555` | demora antes de responder | timeout na validação |
| `6666` | `200`, estado `BLOCKED` | conta indisponível |
| qualquer outro | `200`, estado `ACTIVE` | conta válida |

### `POST /transactions`

Cria uma transferência externa. O corpo contém:

```json
{
  "external_transaction_id": "id-da-operacao",
  "amount": 1000,
  "channel": "PIX",
  "sender": {"bank_code": 1, "branch": 1234, "number": 10},
  "recipient": {"bank_code": 2, "branch": 1, "number": 20}
}
```

O `external_transaction_id` é idempotente: repetir a mesma operação retorna
o mesmo resultado armazenado.

O sufixo da conta destinatária controla o resultado:

| Sufixo | Resposta | Uso |
|---|---|---|
| `9999` | `REJECTED` | rejeição pelo banco externo |
| `7777` | demora apenas na primeira tentativa | timeout inicial e reconciliação |
| `8888` | demora em toda chamada de criação | timeout persistente |
| qualquer outro | `SETTLED` | liquidação normal |

O atraso é configurado por `EXTERNAL_BANK_DELAY_SECONDS`. O timeout usado pela
API é configurado por `EXTERNAL_BANK_API_TIMEOUT`.

### `GET /transactions/{external_transaction_id}`

Consulta uma transferência já criada. A API usa esta rota para reconciliar
uma operação que ficou `EM_ANDAMENTO` após timeout.

### `POST /admin/transactions`

Insere diretamente uma transferência no estado informado (`SETTLED` ou
`REJECTED`). Serve para preparar cenários de teste no mock.

Este endpoint não é chamado pela API durante o fluxo normal e não implementa
o recebimento de uma transferência externa na nossa conta.

## Integração com a API

Na execução com Docker Compose, a API chama:

```text
http://external-bank-fake:8080/accounts/...
http://external-bank-fake:8080/transactions
http://external-bank-fake:8080/transactions/{external_transaction_id}
```

O mock nunca altera diretamente os saldos ou as tabelas do banco principal.
Após `SETTLED`, a API é responsável por efetivar o débito e criar o
lançamento local.
