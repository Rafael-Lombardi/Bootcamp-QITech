# Bank Slip Fake

Simula serviço externo responsável pelo ciclo de vida do boleto.

- `POST /bank_slip` emite boleto com pagador e beneficiário.
- `GET /bank_slip/{bank_slip_key}` retorna valor, vencimento, partes e status.
- `POST /bank_slip/{bank_slip_key}/payment` confirma pagamento idempotente.

O mock começa com as fixtures `fixture-external-open`,
`fixture-external-timeout`, `fixture-expired` e `fixture-paid`.

O fake nunca altera contas do banco. Após `SETTLED`, nossa API cria os
lançamentos locais: débito do pagador e, se o beneficiário for interno,
crédito do beneficiário. Estado fica apenas em memória.
