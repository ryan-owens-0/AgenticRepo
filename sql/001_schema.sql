BEGIN;

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS raw.hud_active_property (
    source_file text NOT NULL,
    source_sheet text NOT NULL,
    source_row integer NOT NULL,
    source_as_of_date date NOT NULL,
    retrieved_at_utc timestamptz NOT NULL,
    source_url text NOT NULL,
    payload_sha256 char(64) NOT NULL,
    raw_record_json jsonb NOT NULL,
    PRIMARY KEY (source_file, source_sheet, source_row)
);

CREATE TABLE IF NOT EXISTS raw.hud_contract_rent (
    source_file text NOT NULL,
    source_sheet text NOT NULL,
    source_row integer NOT NULL,
    source_as_of_date date NOT NULL,
    retrieved_at_utc timestamptz NOT NULL,
    source_url text NOT NULL,
    payload_sha256 char(64) NOT NULL,
    raw_record_json jsonb NOT NULL,
    PRIMARY KEY (source_file, source_sheet, source_row)
);

CREATE TABLE IF NOT EXISTS staging.hud_active_property (
    source_file text NOT NULL,
    source_sheet text NOT NULL,
    source_row integer NOT NULL,
    source_as_of_date date NOT NULL,
    retrieved_at_utc timestamptz NOT NULL,
    payload_sha256 char(64) NOT NULL,
    property_id bigint NOT NULL,
    property_name text,
    city_name text,
    state_code char(2),
    state_name text,
    zip_code text,
    county_code text,
    county_name text,
    msa_code text,
    msa_name text,
    property_category text,
    total_unit_count integer,
    total_assisted_unit_count integer,
    has_active_assistance_ind char(1),
    is_subsidized_ind char(1),
    raw_record_json jsonb NOT NULL,
    PRIMARY KEY (source_file, source_sheet, source_row)
);

CREATE TABLE IF NOT EXISTS staging.hud_contract_rent (
    source_file text NOT NULL,
    source_sheet text NOT NULL,
    source_row integer NOT NULL,
    source_as_of_date date NOT NULL,
    retrieved_at_utc timestamptz NOT NULL,
    payload_sha256 char(64) NOT NULL,
    property_id bigint NOT NULL,
    contract_number text NOT NULL,
    assistance_bedroom_count smallint NOT NULL,
    assistance_unit_count integer NOT NULL,
    contract_rent_amount numeric(17,2) NOT NULL,
    fair_market_rent_amount numeric(17,2) NOT NULL,
    utility_allowance_amount numeric(17,2) NOT NULL,
    raw_record_json jsonb NOT NULL,
    PRIMARY KEY (source_file, source_sheet, source_row)
);

CREATE TABLE IF NOT EXISTS core.dim_hud_property (
    property_id bigint PRIMARY KEY,
    property_name text,
    city_name text,
    state_code char(2),
    state_name text,
    zip_code text,
    county_code text,
    county_name text,
    msa_code text,
    msa_name text,
    property_category text,
    total_unit_count integer,
    total_assisted_unit_count integer,
    has_active_assistance_ind char(1),
    is_subsidized_ind char(1),
    source_file text NOT NULL,
    source_sheet text NOT NULL,
    source_row integer NOT NULL,
    source_as_of_date date NOT NULL,
    retrieved_at_utc timestamptz NOT NULL,
    UNIQUE (source_file, source_sheet, source_row)
);

CREATE TABLE IF NOT EXISTS core.hud_rent_observation (
    observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_id bigint NOT NULL,
    contract_number text NOT NULL,
    assistance_bedroom_count smallint NOT NULL,
    assistance_unit_count integer NOT NULL,
    contract_rent_amount numeric(17,2) NOT NULL,
    fair_market_rent_amount numeric(17,2) NOT NULL,
    utility_allowance_amount numeric(17,2) NOT NULL,
    payload_sha256 char(64) NOT NULL,
    source_file text NOT NULL,
    source_sheet text NOT NULL,
    source_row integer NOT NULL,
    source_as_of_date date NOT NULL,
    retrieved_at_utc timestamptz NOT NULL,
    UNIQUE (source_file, source_sheet, source_row)
);

CREATE INDEX IF NOT EXISTS ix_hud_rent_observation_property
    ON core.hud_rent_observation (property_id);
CREATE INDEX IF NOT EXISTS ix_hud_rent_observation_stated_key
    ON core.hud_rent_observation
       (property_id, contract_number, assistance_bedroom_count);
CREATE INDEX IF NOT EXISTS ix_hud_rent_observation_payload
    ON core.hud_rent_observation (payload_sha256);

COMMENT ON TABLE core.hud_rent_observation IS
    'One row per nonblank HUD workbook observation. Property/contract/bedroom is not unique; amounts are not additive until source grain is resolved.';

COMMIT;
