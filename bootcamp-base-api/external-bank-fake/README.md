# External Bank Fake

Simula outro banco somente para transferências `PIX` e `TED`.

- `GET /accounts/{bank_code}/{branch}/{number}` consulta conta externa.
- `POST /transactions` envia transferência.
- `GET /transactions/{external_transaction_id}` reconcilia transferência.
- `POST /admin/transactions` prepara recebimento vindo de fora.

Boletos não passam por este serviço. Eles usam o `BankSlipConnector` e o
`bank-slip-fake`. Este fake guarda estado apenas em memória.
