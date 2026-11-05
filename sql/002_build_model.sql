BEGIN;

TRUNCATE TABLE
    staging.hud_active_property,
    staging.hud_contract_rent,
    core.dim_hud_property,
    core.hud_rent_observation
RESTART IDENTITY;

INSERT INTO staging.hud_active_property (
    source_file, source_sheet, source_row, source_as_of_date,
    retrieved_at_utc, payload_sha256, property_id, property_name,
    city_name, state_code, state_name, zip_code, county_code,
    county_name, msa_code, msa_name, property_category,
    total_unit_count, total_assisted_unit_count,
    has_active_assistance_ind, is_subsidized_ind, raw_record_json
)
SELECT
    source_file,
    source_sheet,
    source_row,
    source_as_of_date,
    retrieved_at_utc,
    payload_sha256,
    NULLIF(BTRIM(raw_record_json->>'property_id'), '')::bigint,
    NULLIF(BTRIM(raw_record_json->>'property_name_text'), ''),
    NULLIF(BTRIM(raw_record_json->>'city_name_text'), ''),
    NULLIF(BTRIM(raw_record_json->>'state_code'), ''),
    NULLIF(BTRIM(raw_record_json->>'state_name_text'), ''),
    NULLIF(BTRIM(raw_record_json->>'zip_code'), ''),
    NULLIF(BTRIM(raw_record_json->>'county_code'), ''),
    NULLIF(BTRIM(raw_record_json->>'county_name_text'), ''),
    NULLIF(BTRIM(raw_record_json->>'msa_code'), ''),
    NULLIF(BTRIM(raw_record_json->>'msa_name_text'), ''),
    NULLIF(BTRIM(raw_record_json->>'property_category_name'), ''),
    NULLIF(BTRIM(raw_record_json->>'total_unit_count'), '')::integer,
    NULLIF(BTRIM(raw_record_json->>'total_assisted_unit_count'), '')::integer,
    NULLIF(BTRIM(raw_record_json->>'has_active_assistance_ind'), ''),
    NULLIF(BTRIM(raw_record_json->>'is_subsidized_ind'), ''),
    raw_record_json
FROM raw.hud_active_property;

INSERT INTO staging.hud_contract_rent (
    source_file, source_sheet, source_row, source_as_of_date,
    retrieved_at_utc, payload_sha256, property_id, contract_number,
    assistance_bedroom_count, assistance_unit_count,
    contract_rent_amount, fair_market_rent_amount,
    utility_allowance_amount, raw_record_json
)
SELECT
    source_file,
    source_sheet,
    source_row,
    source_as_of_date,
    retrieved_at_utc,
    payload_sha256,
    NULLIF(BTRIM(raw_record_json->>'property_id'), '')::bigint,
    BTRIM(raw_record_json->>'contract_number'),
    NULLIF(BTRIM(raw_record_json->>'assistance_bedroom_count'), '')::smallint,
    NULLIF(BTRIM(raw_record_json->>'assistance_unit_count'), '')::integer,
    NULLIF(BTRIM(raw_record_json->>'contract_rent_amount'), '')::numeric(17,2),
    NULLIF(BTRIM(raw_record_json->>'fair_market_rent_amount'), '')::numeric(17,2),
    NULLIF(BTRIM(raw_record_json->>'utility_allowance_amount'), '')::numeric(17,2),
    raw_record_json
FROM raw.hud_contract_rent;

INSERT INTO core.dim_hud_property (
    property_id, property_name, city_name, state_code, state_name, zip_code,
    county_code, county_name, msa_code, msa_name, property_category,
    total_unit_count, total_assisted_unit_count, has_active_assistance_ind,
    is_subsidized_ind, source_file, source_sheet, source_row,
    source_as_of_date, retrieved_at_utc
)
SELECT
    property_id, property_name, city_name, state_code, state_name, zip_code,
    county_code, county_name, msa_code, msa_name, property_category,
    total_unit_count, total_assisted_unit_count, has_active_assistance_ind,
    is_subsidized_ind, source_file, source_sheet, source_row,
    source_as_of_date, retrieved_at_utc
FROM staging.hud_active_property;

INSERT INTO core.hud_rent_observation (
    property_id, contract_number, assistance_bedroom_count,
    assistance_unit_count, contract_rent_amount,
    fair_market_rent_amount, utility_allowance_amount, payload_sha256,
    source_file, source_sheet, source_row, source_as_of_date, retrieved_at_utc
)
SELECT
    property_id, contract_number, assistance_bedroom_count,
    assistance_unit_count, contract_rent_amount,
    fair_market_rent_amount, utility_allowance_amount, payload_sha256,
    source_file, source_sheet, source_row, source_as_of_date, retrieved_at_utc
FROM staging.hud_contract_rent;

CREATE OR REPLACE VIEW mart.vw_hud_property_overview AS
SELECT
    state_code,
    state_name,
    county_code,
    county_name,
    msa_code,
    msa_name,
    property_category,
    COUNT(DISTINCT property_id) AS hud_property_count,
    SUM(total_unit_count) AS hud_reported_total_units,
    SUM(total_assisted_unit_count) AS hud_reported_assisted_units
FROM core.dim_hud_property
GROUP BY
    state_code, state_name, county_code, county_name,
    msa_code, msa_name, property_category;

CREATE OR REPLACE VIEW mart.vw_hud_rent_observation AS
WITH stated_key_stats AS (
    SELECT
        property_id,
        contract_number,
        assistance_bedroom_count,
        COUNT(*) AS stated_key_row_count,
        COUNT(DISTINCT payload_sha256) AS stated_key_distinct_payload_count
    FROM core.hud_rent_observation
    GROUP BY property_id, contract_number, assistance_bedroom_count
),
exact_payload_stats AS (
    SELECT payload_sha256, COUNT(*) AS exact_payload_copy_count
    FROM core.hud_rent_observation
    GROUP BY payload_sha256
)
SELECT
    r.observation_id,
    r.property_id,
    r.contract_number,
    r.assistance_bedroom_count,
    r.assistance_unit_count,
    r.contract_rent_amount,
    r.fair_market_rent_amount,
    r.utility_allowance_amount,
    r.contract_rent_amount + r.utility_allowance_amount AS row_gross_amount,
    CASE
        WHEN r.fair_market_rent_amount > 0
        THEN (r.contract_rent_amount + r.utility_allowance_amount)
             / r.fair_market_rent_amount
        ELSE NULL
    END AS row_gross_to_fmr_ratio,
    CASE WHEN p.property_id IS NULL
        THEN 'unmatched_property_id'
        ELSE 'matched_property_id'
    END AS property_match_status,
    p.property_name,
    p.city_name,
    p.state_code,
    p.state_name,
    p.county_code,
    p.county_name,
    p.msa_code,
    p.msa_name,
    p.property_category,
    s.stated_key_row_count,
    s.stated_key_distinct_payload_count,
    e.exact_payload_copy_count,
    r.source_file,
    r.source_sheet,
    r.source_row,
    r.source_as_of_date,
    r.retrieved_at_utc,
    r.payload_sha256
FROM core.hud_rent_observation AS r
LEFT JOIN core.dim_hud_property AS p
    ON p.property_id = r.property_id
LEFT JOIN stated_key_stats AS s
    ON s.property_id = r.property_id
    AND s.contract_number = r.contract_number
    AND s.assistance_bedroom_count = r.assistance_bedroom_count
LEFT JOIN exact_payload_stats AS e
    ON e.payload_sha256 = r.payload_sha256;

CREATE OR REPLACE VIEW mart.vw_hud_source_quality AS
SELECT
    (SELECT COUNT(*) FROM core.dim_hud_property) AS hud_property_rows,
    (SELECT COUNT(*) FROM core.hud_rent_observation) AS hud_rent_observation_rows,
    (SELECT COUNT(*) FROM core.hud_rent_observation r
        LEFT JOIN core.dim_hud_property p USING (property_id)
        WHERE p.property_id IS NULL) AS unmatched_rent_observation_rows,
    (SELECT COUNT(*) FROM (
        SELECT property_id, contract_number, assistance_bedroom_count
        FROM core.hud_rent_observation
        GROUP BY property_id, contract_number, assistance_bedroom_count
        HAVING COUNT(*) > 1
    ) AS duplicate_keys) AS nonunique_property_contract_bedroom_key_groups,
    (SELECT COUNT(*) FROM (
        SELECT payload_sha256
        FROM core.hud_rent_observation
        GROUP BY payload_sha256
        HAVING COUNT(*) > 1
    ) AS duplicate_payloads) AS exact_payload_copy_groups;

COMMIT;

