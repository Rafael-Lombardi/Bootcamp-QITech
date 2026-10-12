# Bank Slip Fake

Simula serviço externo responsável pelo ciclo de vida do boleto.

- `POST /bank_slip` emite boleto com pagador e beneficiário.
- `GET /bank_slip/{bank_slip_key}` retorna valor, vencimento, partes e status.
- `POST /bank_slip/{bank_slip_key}/payment` confirma pagamento idempotente.

O mock começa com as fixtures `fixture-external-open`,
`fixture-external-timeout`, `fixture-expired` e `fixture-paid`.

| Fixture | Valor | Estado | Uso |
|---|---:|---|---|
| `fixture-external-open` | R$ 10,00 | `OPEN` | Pagamento normal; liquida e vira `PAID`. |
| `fixture-external-timeout` | R$ 7,50 | `OPEN` | Liquida, mas responde após o timeout; repetir a mesma chave reconcilia. |
| `fixture-expired` | R$ 5,00 | vencido | Rejeita pagamento por expiração. |
| `fixture-paid` | R$ 6,00 | `PAID` | Rejeita nova tentativa como duplicada. |

Use-as em `POST /boleto/{bank_slip_key}/pagamento`, com uma conta interna como
`pagador` e chave de idempotência. As fixtures têm beneficiário externo; nenhum
crédito local é criado. O estado fica em memória; reinicie o mock para
restaurá-las: `docker compose restart bank-slip-fake`.

O fake nunca altera contas do banco. Após `SETTLED`, nossa API cria os
lançamentos locais: débito do pagador e, se o beneficiário for interno,
crédito do beneficiário. Estado fica apenas em memória.
