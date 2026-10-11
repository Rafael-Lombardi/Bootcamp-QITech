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
