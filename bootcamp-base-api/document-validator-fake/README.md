# Document Validator Fake

Simula um birô externo que consulta a situação cadastral de `CPF` e `CNPJ` na
Receita. Como nos birôs reais, cada documento tem a sua rota.

- `GET /cpf/{cpf}` consulta CPF (11 dígitos): `REGULAR` ou `SUSPENSA`.
- `GET /cnpj/{cnpj}` consulta CNPJ (14 dígitos): `ATIVA` ou `INAPTA`.

O número vai só com dígitos. Formato errado, dígito verificador errado ou todos
os dígitos iguais respondem `422`. Documento válido que começa com `1234` volta
com a situação irregular. Exemplos:

| Documento        | Resposta                                          |
| ---------------- | ------------------------------------------------- |
| `52998224725`    | `{"cpf": "52998224725", "status": "REGULAR"}`     |
| `12340000084`    | `{"cpf": "12340000084", "status": "SUSPENSA"}`    |
| `11222333000181` | `{"cnpj": "11222333000181", "status": "ATIVA"}`   |
| `12340000000039` | `{"cnpj": "12340000000039", "status": "INAPTA"}`  |

Este fake não guarda estado.
