CREATE TABLE sample_entity_status(
    id		                        SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO sample_entity_status (enumerator) VALUES
('created'),
('pending'),
('success'),
('failed');

CREATE TABLE sample_entity(
    id                              SERIAL PRIMARY KEY,
    sample_entity_key               CHAR(36) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    sample_entity_data              JSONB NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    birthdate                       DATE NOT NULL,
    counter                         INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(sample_entity_key),
    UNIQUE(document_number),
    UNIQUE(email)
);

CREATE TABLE sample_entity_status_event(
    id                              SERIAL PRIMARY KEY,
    sample_entity_id                INTEGER NOT NULL REFERENCES sample_entity(id),
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE client(
    id                              SERIAL PRIMARY KEY,
    client_key                      CHAR(36) NOT NULL,
    client_type                     VARCHAR(2) NOT NULL,
    document_number                 VARCHAR(14) NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    corporate_name                  VARCHAR(255),
    birthdate                       DATE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(client_key),
    UNIQUE(document_number),
    CHECK(client_type IN ('PF', 'PJ')),
    CHECK(
        (client_type = 'PF' AND birthdate IS NOT NULL AND corporate_name IS NULL)
        OR
        (client_type = 'PJ' AND birthdate IS NULL AND corporate_name IS NOT NULL)
    )
);

CREATE TABLE account(
    id                              SERIAL PRIMARY KEY,
    account_key                     CHAR(36) NOT NULL,
    bank_id                         INTEGER NOT NULL,
    branch                          INTEGER NOT NULL,
    number                          INTEGER NOT NULL,
    client_id                       INTEGER NOT NULL REFERENCES client(id),
    balance_cents                   BIGINT NOT NULL DEFAULT(0),
    status                          VARCHAR(20) NOT NULL DEFAULT('PENDENTE'),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(account_key),
    UNIQUE(bank_id, branch, number),
    CHECK(bank_id > 0),
    CHECK(branch > 0),
    CHECK(number > 0),
    CHECK(balance_cents >= 0),
    CHECK(status IN ('PENDENTE', 'ATIVA', 'BLOQUEADA', 'DESATIVADA'))
);

CREATE TABLE account_status_event(
    id                              SERIAL PRIMARY KEY,
    account_id                     INTEGER NOT NULL REFERENCES account(id),
    status                          VARCHAR(20) NOT NULL,
    reason                          VARCHAR(255) NOT NULL,
    event_datetime                  TIMESTAMP NOT NULL DEFAULT(NOW()),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    CHECK(status IN ('PENDENTE', 'ATIVA', 'BLOQUEADA', 'DESATIVADA'))
);

CREATE TABLE bank_transaction(
    id                              SERIAL PRIMARY KEY,
    transaction_key                CHAR(36) NOT NULL,
    idempotency_key                CHAR(36) NOT NULL,
    sender_bank_id                 INTEGER NOT NULL,
    sender_branch                  INTEGER NOT NULL,
    sender_number                  INTEGER NOT NULL,
    recipient_bank_id              INTEGER NOT NULL,
    recipient_branch               INTEGER NOT NULL,
    recipient_number               INTEGER NOT NULL,
    amount_cents                    BIGINT NOT NULL,
    fee_cents                       BIGINT NOT NULL DEFAULT(0),
    channel                         VARCHAR(10) NOT NULL,
    status                          VARCHAR(20) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(transaction_key),
    UNIQUE(idempotency_key),
    CHECK(amount_cents > 0),
    CHECK(fee_cents >= 0),
    CHECK(sender_bank_id > 0),
    CHECK(sender_branch > 0),
    CHECK(sender_number > 0),
    CHECK(recipient_bank_id > 0),
    CHECK(recipient_branch > 0),
    CHECK(recipient_number > 0),
    CHECK(channel IN ('PIX', 'TED')),
    CHECK(status IN ('CONCLUIDA', 'EM_ANDAMENTO', 'CANCELADA', 'FALHOU'))
);

CREATE TABLE account_entry(
    id                              SERIAL PRIMARY KEY,
    transaction_id                 INTEGER NOT NULL REFERENCES bank_transaction(id),
    account_id                     INTEGER NOT NULL REFERENCES account(id),
    movement_cents                 BIGINT NOT NULL,
    created_at                     TIMESTAMP NOT NULL DEFAULT(NOW()),
    CHECK(movement_cents <> 0)
);
