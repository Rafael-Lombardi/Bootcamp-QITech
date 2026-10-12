# Bootcamp QI Tech — API bancária

API REST para clientes, contas, transferências PIX/TED, boletos e extrato.
O projeto usa Python, FastAPI, PostgreSQL e Docker.

## 1. Executando localmente

### Pré-requisitos

| Ferramenta | Uso | Como conferir |
|---|---|---|
| Docker Compose | API, banco e mocks externos | `docker compose version` |
| Git | obter o projeto | `git --version` |
| Python 3.11+ | executar os testes | `python3 --version` |

Suba todos os serviços:

```bash
docker compose up
```

Na primeira execução o Docker cria as imagens, inicializa o PostgreSQL e
sobe a API. Aguarde a mensagem `Application startup complete` ou o status
`healthy` do serviço `api`.

Serviços principais:

| Serviço | Função |
|---|---|
| `api` | API bancária |
| `db` | PostgreSQL |
| `external-bank-fake` | mock do banco externo para PIX/TED |
| `bank-slip-fake` | mock do registro e liquidação de boletos |
| `document-validator-fake` | mock da validação de documentos |

Verifique a API:

```bash
curl http://localhost:3000/
curl -i http://localhost:3000/health_check
```

As respostas esperadas são `200` na rota raiz e `204` no healthcheck. A
resposta da raiz contém o nome do serviço e o PID do processo.

Para desligar os serviços:

```bash
docker compose down
```

## 2. Configuração e autenticação

O projeto funciona com os valores padrão do `docker-compose.yml`. Para
alterar portas, tokens ou endereços externos:

```bash
cp .env.example .env
```

O `.env` é local e não deve ser commitado. O `.env.example` contém apenas
valores de exemplo.

As rotas de negócio exigem:

```http
INTERNAL-TOKEN: default_token
```

O valor pode ser alterado com `INTERNAL_TOKEN` no `.env`. Somente estas rotas
são públicas:

- `GET /`
- `GET /health_check`

Os tokens `BANKSLIP_API_INTERNAL_TOKEN` e
`EXTERNAL_BANK_API_INTERNAL_TOKEN` são diferentes: eles autenticam a API
quando ela chama os mocks externos.

Se a API ou o banco forem executados fora do Docker, ajuste também
`DATABASE_URL`, `SERVER_LOCALHOST` e as URLs dos mocks no `.env`. Dentro do
Compose, a API usa os nomes dos serviços, como `db:5432` e
`bank-slip-fake:8080`.

## 3. Endpoints

Todas as rotas abaixo, exceto as duas públicas mencionadas anteriormente,
exigem `INTERNAL-TOKEN`.

| Método e rota | Função | Resposta principal |
|---|---|---|
| `POST /cliente` | cadastra PF ou PJ | `201` ao criar; `200` ao repetir os mesmos dados |
| `GET /cliente/{chave_cliente}` | consulta cliente e contas | `200` |
| `POST /cliente/{chave_cliente}/conta` | abre conta | `201` ao criar; `200` ao repetir agência e número |
| `GET /conta/{chave_conta}` | consulta conta, estado e saldo | `200` |
| `PATCH /conta/{chave_conta}` | altera estado da conta | `200` |
| `GET /conta/{chave_conta}/transacao` | consulta o extrato | `200` |
| `POST /transacao` | executa PIX ou TED | `201` ao criar; `200` ao repetir a chave |
| `POST /boleto` | emite boleto para beneficiário interno | `201` ao registrar; `200` ao repetir a chave |
| `POST /boleto/{chave_boleto}/pagamento` | paga boleto | `201` ao liquidar; `200` ao repetir ou reconciliar |

### Clientes e contas

Clientes podem ser pessoa física ou jurídica. Uma conta é associada a um
cliente e começa no estado `PENDENTE`. A conta precisa estar ativa para
participar de operações financeiras.

A desativação exige saldo zero e nenhuma transação em andamento.

Exemplo de criação de cliente:

```bash
curl -X POST http://localhost:3000/cliente \
  -H "INTERNAL-TOKEN: default_token" \
  -H "Content-Type: application/json" \
  -d '{
    "documento": "52998224725",
    "nome": "Maria da Silva",
    "nascimento": "1990-05-17"
  }'
```

Repetir o cadastro com os mesmos dados é idempotente. O mesmo documento
com dados incompatíveis retorna conflito.

### PIX e TED

`POST /transacao` aceita transferências para contas internas ou para outro
banco. Quando o destinatário é externo, a API:

1. valida os dados do destinatário;
2. cria a transação local como `EM_ANDAMENTO`;
3. chama o `external-bank-fake` sem manter lock da conta;
4. em `SETTLED`, efetiva o débito e os lançamentos locais;
5. em `REJECTED`, marca a transação como `FALHOU`;
6. em timeout, mantém a transação pendente para reconciliação.

Um timeout não significa que o banco externo rejeitou a operação. A
conciliação usa o identificador externo e a mesma chave de idempotência.

### Boletos

#### Emissão

`POST /boleto` recebe beneficiário, valor, vencimento e dados do pagador.
O beneficiário precisa ser uma conta interna válida e ativa. A API registra
essa associação local antes de solicitar a emissão ao `bank-slip-fake` e
persiste a chave retornada pelo mock.

O beneficiário é associado à conta validada, não inferido apenas pelo banco,
agência ou número informados pelo boleto.

#### Pagamento

`POST /boleto/{chave_boleto}/pagamento` recebe a conta pagadora no corpo e a
chave de idempotência no header `chave_de_idempotencia`.

O fluxo é:

1. consulta o boleto no `bank-slip-fake`;
2. valida estado, valor, vencimento e pagador;
3. cria uma transação local `EM_ANDAMENTO`;
4. solicita o pagamento ao mock sem manter lock da conta;
5. após `SETTLED`, debita o pagador e cria os lançamentos locais;
6. se o boleto foi emitido internamente, credita a conta beneficiária registrada.

Boletos externos não criam crédito em conta local. O pagamento não cobra
tarifa.

O boleto não pode ser liquidado duas vezes. Um timeout mantém a transação
pendente; repetir a mesma chave permite reconciliar o resultado sem criar
movimentação duplicada.

### Extrato

`GET /conta/{chave_conta}/transacao` consulta os lançamentos da conta,
ordenados do mais novo para o mais antigo.

Parâmetros:

| Parâmetro | Regra |
|---|---|
| `limite` | opcional, padrão `20`, entre `1` e `100` |
| `proxima` | cursor retornado pela página anterior |

O extrato é construído a partir de `account_entry`, com contexto da operação
obtido por `JOIN` com `bank_transaction`. A última página retorna
`"proxima": null`.

## 4. Idempotência e operações externas

O cliente deve persistir a chave de idempotência e reutilizá-la quando a
resposta for perdida ou ocorrer timeout. A API também persiste a chave junto
da transação.

Regras principais:

- mesma chave e mesmo payload: retorna ou retoma a operação existente;
- mesma chave e payload incompatível: retorna conflito;
- chave diferente: representa uma nova operação;
- não existe retry automático em background;
- timeout externo não é tratado como falha definitiva;
- liquidação e criação dos lançamentos locais são idempotentes.

No pagamento de boleto, a própria chave do boleto também impede uma segunda
liquidação. Essa proteção complementa, mas não substitui, a idempotência da
transação local.

## 5. Mock de boletos

O `bank-slip-fake` mantém suas fixtures em memória:

| Fixture | Valor | Estado | Uso |
|---|---:|---|---|
| `fixture-external-open` | R$ 10,00 | `OPEN` | pagamento normal |
| `fixture-external-timeout` | R$ 7,50 | `OPEN` | liquida, mas responde após o timeout |
| `fixture-expired` | R$ 5,00 | vencido | rejeição por expiração |
| `fixture-paid` | R$ 6,00 | `PAID` | rejeição por boleto já pago |

As fixtures têm beneficiário externo, portanto não geram crédito local.
Após testes de pagamento, restaure o estado do mock com:

```bash
docker compose restart bank-slip-fake
```

O mock nunca altera diretamente o saldo ou chama endpoints internos do
banco.

## 6. Testes

Os testes rodam na máquina local, contra a API e os mocks que estão no
Docker. Instale as dependências uma vez:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

No Windows, use `.venv\Scripts\activate` para ativar o ambiente virtual.

Com a API saudável:

```bash
pytest
```

Para executar um teste específico:

```bash
pytest -v tests/integration/test_healthcheck.py
```

Os testes conversam com a API por HTTP. A exceção é
`tests/utils/db_utils.py`, usada para recriar o schema entre cenários que
dependem de um banco limpo.

## 7. Arquitetura

```text
src/
  app.py           registra rotas e middlewares
  constants.py     configurações do ambiente
  database.py      sessão do banco
  resources/       entrada e saída HTTP
  schemas/         validação dos payloads
  controllers/     regras de negócio
  repositories/    acesso ao banco
  models/          tabelas SQLAlchemy
  dtos/            transformação para resposta JSON
  errors/          erros e códigos da API
  middlewares/     comportamento comum das requisições
  connectors/      chamadas aos serviços externos
  utils/           utilitários compartilhados

database/
  database.sql     schema inicial do PostgreSQL

tests/
  testes de integração da API
```

Fluxo principal:

```text
requisição → resource → controller → repository → banco
                         ↓
                      connector → serviço externo
```

O resource trata HTTP, o controller aplica as regras de negócio, o
repository conversa com o banco e o connector encapsula integrações
externas.

## 8. Troubleshooting

### `port is already allocated`

Outra aplicação já usa uma porta. Copie o arquivo de ambiente e altere as
portas necessárias:

```bash
cp .env.example .env
```

Por exemplo:

```dotenv
API_PORT=3001
DB_PORT=5433
DATABASE_URL=postgresql+psycopg2://bootcamp:bootcamp@localhost:5433/bootcamp
```

### Docker não está disponível

Inicie o Docker Desktop ou o serviço do Docker no sistema operacional.

### `relation "..." does not exist`

O `database/database.sql` é executado quando o volume do banco é criado.
Depois de alterar esse arquivo, recrie o volume:

```bash
docker compose down -v
docker compose up
```

Esse comando apaga os dados locais do banco. Use-o apenas quando puder
perder os dados criados durante o desenvolvimento.

### Ver logs

```bash
docker compose logs -f api
```

## 9. Códigos de erro

Todos os erros seguem este formato:

```json
{
  "title": "Bad Request",
  "description": "mensagem técnica",
  "translation": "mensagem para o cliente",
  "code": "QIT000001"
}
```

| Código | Significado |
|---|---|
| `QIT000001` | payload fora do formato esperado |
| `QIT000002` | `INTERNAL-TOKEN` ausente ou inválido |
| `QIT000010` | parâmetros da requisição se contradizem |
| `QIT000404` | rota ou recurso inexistente |
| `QIT000405` | método não permitido |
| `QIT000500` | erro inesperado |
| `QIT001001` | cliente inexistente |
| `QIT001002` | CPF ou CNPJ inválido |
| `QIT001003` | documento já cadastrado com dados diferentes |
| `QIT001004` | pessoa física menor de 18 anos |
| `QIT001005` | conta inexistente |
| `QIT001006` | agência e número pertencem a outro cliente |
| `QIT001007` | cliente atingiu o limite de contas |
| `QIT001009` | conta possui saldo ao ser desativada |
| `QIT001010` | conta possui transação em andamento ao ser desativada |
| `QIT001013` | conta remetente inexistente |
| `QIT001014` | conta destinatária inexistente |
| `QIT001015` | conta destinatária externa inexistente |
| `QIT001016` | conta remetente inativa |
| `QIT001017` | conta destinatária indisponível |
| `QIT001018` | conta destinatária externa indisponível |
| `QIT001019` | banco externo rejeitou a transação |
| `QIT001020` | banco externo não respondeu a tempo |
| `QIT001021` | saldo insuficiente para valor e tarifa |
| `QIT001022` | chave de idempotência já usada |
| `QIT001023` | remetente e destinatário são a mesma conta |
| `QIT001024` | boleto inexistente |
| `QIT001025` | boleto vencido |
| `QIT001026` | boleto já pago |
| `QIT001027` | pagamento incompatível em andamento |
| `QIT001028` | serviço de boletos não respondeu a tempo |
| `QIT001029` | serviço de boletos rejeitou a operação |
| `QIT001030` | cursor do extrato inexistente ou de outra conta |
| `QIT001031` | beneficiário externo diverge do registro local |

Os códigos `QIT000...` representam erros gerais da API. Os códigos
`QIT001...` representam regras de negócio. Eles são verificados na subida
da aplicação para impedir duplicidade.

## 10. Licença

Este projeto está sob a licença MIT.
