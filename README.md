# HUD Multifamily Public Data Portfolio

This project is the first executable slice of the REBA public-stack workback:

HUD source workbooks → Python source-row loader → PostgreSQL raw/staging/core layers → Apache Ossie semantic contract → Power BI and Paginated Report Builder.

The current build covers the HUD source and PostgreSQL foundation. It preserves source rows and records provenance. The rent workbook's apparent property/contract/bedroom key is not unique, so rent aggregation and weighting are held until that row grain is explained.

## Current evidence

- HUD's October 6, 2026 property workbook has 37,438 nonblank rows in its property-level sheet and a unique, populated property ID.
- The workbook also contains a separate FHA-number sheet at a different grain. It is recorded in the source profile and excluded from the property dimension.
- The October 6, 2026 rent workbook has two matching-schema sheets and 73,298 nonblank source rows. The first worksheet contains 34,286 formatted blank rows; these are not loaded as records.
- property_id + contract_number + bedroom_count repeats in 40,123 excess rows and 27,741 key groups have differing row payloads. The source file does not include another obvious row key. Each source observation is retained with workbook, worksheet, and row number.
- Within the repeated groups, 26,536 contain multiple FMR amounts, 5,077 contain multiple assistance-unit counts, 4,793 contain multiple contract-rent amounts, and 3,313 contain multiple utility-allowance amounts.
- 800 exact payload copies occur across the rent sheets. They are preserved and flagged; no deduplication rule is assumed.
- 9,935 rent rows (1,794 distinct property IDs) do not match the active property-level sheet. The SQL view keeps them with an unmatched status.
- The property field dictionary is dated July 2010. Current workbook headers are captured directly; meanings for fields absent from the old dictionary remain unverified.

See artifacts/source-profile-2026-11-05.json for counts, sheet names, source hashes, and data-quality findings. The database readback is in artifacts/database-snapshot-2026-11-05.json. The original downloaded files stay under data/raw/ and are excluded from version control.

## Local environment

Python 3.13 and Docker Desktop are available. The loader uses only Python's standard library, so it has no separate package-install step. PostgreSQL runs in a local 16.15 container bound only to 127.0.0.1; the container was healthy at the latest check and uses the ignored .env file and a named Docker volume. The Windows PostgreSQL command-line tools are not installed; `psql` is available inside the database container.

Power BI Desktop x64 (2.159.1231.0), Power BI Report Builder (15.7.1821.21), and psqlODBC 18.00.0006 x64 are installed. The registered 64-bit PostgreSQL Unicode ODBC driver opens a fresh connection using the local `.env` credentials and reads 37,438 property rows. Power BI Desktop's bundled Npgsql 4.0.17 also connects and reads 37,438 properties and 73,298 rent observations. Report Builder's connection test reaches PostgreSQL but fails password authentication for user `portfolio`, so its end-to-end connection is not yet verified. See the latest entry in `docs/build-log-2026-11-05.md`.

Create a local password file by copying .env.example to .env and replacing the password. Then:

    py -3.13 src/portfolio_pipeline.py download
    docker compose up -d db
    py -3.13 src/portfolio_pipeline.py load

The download command fetches only missing source files. The load command reads the saved files, writes ignored intermediate CSVs, profiles the workbooks, then replaces this project's local raw/staging/core rows. It does not alter other containers or databases.

To stop the local database while keeping its data:

    docker compose stop db

To profile the existing local sources and regenerate the source profile:

    py -3.13 src/portfolio_pipeline.py profile

To download any missing source files:

    py -3.13 src/portfolio_pipeline.py download

The source filenames and as-of date are pinned to HUD's 2026-10-06 capture. Before using a newer HUD release, verify its date on HUD's dataset page and update the pinned filenames and source date in the loader; do not overwrite this snapshot under its old date.

To inspect the database from a local client, use host 127.0.0.1, port 5432, database portfolio, and the local credentials from .env.

## Model boundaries

- core.dim_hud_property is one row per HUD property ID.
- core.hud_rent_observation is one row per nonblank workbook row, keyed by the original filename, worksheet, and Excel row number.
- mart.vw_hud_rent_observation exposes row-level contract rent, utility allowance, gross amount, and FMR ratio, plus duplicate-key and property-match flags. Those amount fields are not additive measures.
- mart.vw_hud_property_overview aggregates property-level counts and HUD-reported unit counts without joining the rent observations.
- No weighted average, rent total, or contract-bedroom fact is published while the rent grain is unresolved.

## Apache Ossie

semantics/hud_multifamily_ossie.yaml uses Apache Ossie's flat document shape and pins the draft spec version 0.2.0.dev0, observed at Apache Ossie commit 172a3e566f2fc9c0a733ebbb470e97c33d2bd8b1. The format and semantics are evolving. The YAML is a manual semantic contract; it does not automatically generate SQL, DAX, or RDL. See semantics/mapping-ledger.csv for the explicit bindings and their status.

## Reporting work not yet built

There is no PBIX, RDL, or PDF in this checkout yet. A direct 64-bit ODBC query works, but Report Builder's Test Connection still fails password authentication for user `portfolio`; verify a live query preview after resolving that connection path. The next report step is a property overview and a source-quality page. The rent/assistance page and paginated rent summary depend on resolving the repeated rent rows and confirming amount comparability. No output should describe this HUD extract as all rental housing or infer occupancy, revenue, NOI, or operator performance.

## Public sources

- [HUD Multifamily Property / Contract / Rent & Utility Allowance datasets](https://www.hud.gov/hud-partners/multifamily-preservation)
- [HUD property data element dictionary](https://www.hud.gov/sites/documents/activemfpropertypded.pdf)
- [HUD contract rent and utility allowance dictionary](https://www.hud.gov/sites/documents/contractsrentutilityallded.pdf)
- [Apache Ossie core specification pinned to the observed commit](https://github.com/apache/ossie/blob/172a3e566f2fc9c0a733ebbb470e97c33d2bd8b1/core-spec/spec.md)
- [Power BI PostgreSQL prerequisites](https://learn.microsoft.com/en-us/power-bi/desktop-data-source-prerequisites)
- [Report Builder ODBC support](https://learn.microsoft.com/en-us/power-bi/paginated-reports/paginated-reports-odbc-support)

