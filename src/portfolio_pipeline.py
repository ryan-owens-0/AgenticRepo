from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import posixpath
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen
from zipfile import ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
ARTIFACT_DIR = ROOT / "artifacts"
SOURCE_AS_OF = date(2026, 10, 6)

SOURCES = {
    "active_multifamily_portfolio_20261006.xlsx": (
        "https://www.hud.gov/sites/dfiles/Housing/documents/activeportfoliopropdata.xlsx",
        "property_workbook",
    ),
    "contracts_rent_utility_allowance_20261006.xlsx": (
        "https://www.hud.gov/sites/dfiles/Housing/documents/contractsrentutilityamt.xlsx",
        "rent_workbook",
    ),
    "active_multifamily_property_ded_2010.pdf": (
        "https://www.hud.gov/sites/documents/activemfpropertypded.pdf",
        "property_dictionary",
    ),
    "contract_rent_utility_allowance_ded.pdf": (
        "https://www.hud.gov/sites/documents/contractsrentutilityallded.pdf",
        "rent_dictionary",
    ),
}

PROPERTY_SHEET = "Step_01_Property_Level_data"
EXCLUDED_PROPERTY_SHEET = "All active Properties with FHA"
RENT_SHEETS = (
    "Contracts_with_Rent_amt_and_Uti",
    "Contracts_w_Rent_amt_and_Uti -2",
)
RENT_HEADERS = [
    "property_id",
    "contract_number",
    "assistance_bedroom_count",
    "assistance_unit_count",
    "contract_rent_amount",
    "fair_market_rent_amount",
    "utility_allowance_amount",
]
PROPERTY_REQUIRED_HEADERS = {
    "property_id",
    "property_name_text",
    "city_name_text",
    "state_code",
    "total_unit_count",
    "total_assisted_unit_count",
    "property_category_name",
    "has_active_assistance_ind",
}
RAW_CSV_HEADERS = [
    "source_file",
    "source_sheet",
    "source_row",
    "source_as_of_date",
    "retrieved_at_utc",
    "source_url",
    "payload_sha256",
    "raw_record_json",
]
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_payload(record: dict[str, str]) -> str:
    encoded = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def column_index(cell_reference: str) -> int:
    value = 0
    for character in cell_reference:
        if not character.isalpha():
            break
        value = value * 26 + ord(character.upper()) - ord("A") + 1
    return value - 1


def workbook_targets(archive: ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target_by_id = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall(f"{{{PKG_REL_NS}}}Relationship")
    }
    result: list[tuple[str, str]] = []
    for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
        target = target_by_id[sheet.attrib[f"{{{REL_NS}}}id"]]
        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = posixpath.normpath(posixpath.join("xl", target))
        result.append((sheet.attrib["name"], target))
    return result


def shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(part.text or "" for part in item.iter() if part.tag.endswith("}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def read_cell_values(row: ET.Element, strings: list[str]) -> list[str]:
    cells = row.findall(f"{{{MAIN_NS}}}c")
    if not cells:
        return []
    values = [""] * (max(column_index(cell.attrib["r"]) for cell in cells) + 1)
    for cell in cells:
        index = column_index(cell.attrib["r"])
        cell_type = cell.attrib.get("t")
        inline = cell.find(f"{{{MAIN_NS}}}is")
        value_node = cell.find(f"{{{MAIN_NS}}}v")
        if cell_type == "inlineStr" and inline is not None:
            value = "".join(part.text or "" for part in inline.iter())
        elif value_node is not None:
            value = value_node.text or ""
            if cell_type == "s":
                value = strings[int(value)]
            elif cell_type == "b":
                value = "Y" if value == "1" else "N"
        else:
            value = ""
        values[index] = value
    return values


def iter_sheet_events(
    workbook_path: Path, requested_sheet: str
):
    with ZipFile(workbook_path) as archive:
        targets = dict(workbook_targets(archive))
        if requested_sheet not in targets:
            raise ValueError(
                f"Worksheet {requested_sheet!r} was not found in {workbook_path.name}."
            )
        strings = shared_strings(archive)
        header: list[str] | None = None
        with archive.open(targets[requested_sheet]) as stream:
            for _, row in ET.iterparse(stream, events=("end",)):
                if not row.tag.endswith("}row"):
                    continue
                row_number = int(row.attrib.get("r", "0"))
                values = read_cell_values(row, strings)
                if header is None:
                    if not any(value.strip() for value in values):
                        row.clear()
                        continue
                    while values and not values[-1]:
                        values.pop()
                    header = [
                        value.strip() if value.strip() else f"_unnamed_column_{i + 1}"
                        for i, value in enumerate(values)
                    ]
                    if len(header) != len(set(header)):
                        raise ValueError(
                            f"Worksheet {requested_sheet!r} has repeated header names."
                        )
                    yield "header", row_number, header
                elif not any(value.strip() for value in values):
                    yield "blank", row_number, None
                else:
                    padded = values[: len(header)] + [""] * max(
                        0, len(header) - len(values)
                    )
                    record = dict(zip(header, padded[: len(header)]))
                    yield "data", row_number, record
                row.clear()
        if header is None:
            raise ValueError(f"Worksheet {requested_sheet!r} has no header row.")


def workbook_sheet_names(path: Path) -> list[str]:
    with ZipFile(path) as archive:
        return [name for name, _ in workbook_targets(archive)]


def int_value(value: str) -> int:
    numeric = Decimal(value.strip())
    if not numeric.is_finite() or numeric != numeric.to_integral_value():
        raise ValueError(f"Not an integer: {value!r}")
    return int(numeric)


def decimal_value(value: str) -> Decimal:
    numeric = Decimal(value.strip())
    if not numeric.is_finite():
        raise ValueError(f"Not a finite decimal: {value!r}")
    return numeric


def download_sources() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for filename, (url, _) in SOURCES.items():
        destination = RAW_DIR / filename
        if destination.exists():
            print(f"Keeping existing source: {filename}")
            continue
        request = Request(url, headers={"User-Agent": "OpenSourcePortfolio/0.1"})
        temporary = destination.with_suffix(destination.suffix + ".part")
        with urlopen(request, timeout=90) as response, temporary.open("wb") as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                output.write(block)
        temporary.replace(destination)
        print(f"Downloaded: {filename}")


def extract_workbook(
    workbook_path: Path,
    selected_sheets: tuple[str, ...],
    csv_path: Path,
    source_url: str,
    retrieved_at: str,
    source_hash: str,
    callback,
) -> dict[str, dict]:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    profiles: dict[str, dict] = {}
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(RAW_CSV_HEADERS)
        for sheet_name in selected_sheets:
            sheet_profile = {
                "headers": [],
                "data_rows": 0,
                "blank_rows": 0,
                "loaded": True,
            }
            profiles[sheet_name] = sheet_profile
            got_header = False
            for event, source_row, value in iter_sheet_events(
                workbook_path, sheet_name
            ):
                if event == "header":
                    headers = value
                    sheet_profile["headers"] = headers
                    got_header = True
                    if sheet_name == PROPERTY_SHEET:
                        missing = PROPERTY_REQUIRED_HEADERS - set(headers)
                        if missing:
                            raise ValueError(
                                "Property worksheet is missing required headers: "
                                + ", ".join(sorted(missing))
                            )
                    elif sheet_name in RENT_SHEETS and headers != RENT_HEADERS:
                        raise ValueError(
                            f"Unexpected headers in {sheet_name}: {headers!r}"
                        )
                    continue
                if event == "blank":
                    sheet_profile["blank_rows"] += 1
                    continue
                record = value
                payload_hash = sha256_payload(record)
                sheet_profile["data_rows"] += 1
                writer.writerow(
                    [
                        workbook_path.name,
                        sheet_name,
                        source_row,
                        SOURCE_AS_OF.isoformat(),
                        retrieved_at,
                        source_url,
                        payload_hash,
                        json.dumps(
                            record, ensure_ascii=False, separators=(",", ":")
                        ),
                    ]
                )
                callback(sheet_name, source_row, record, payload_hash)
            if not got_header:
                raise ValueError(f"No header read from {sheet_name!r}.")
    return profiles


def count_excluded_sheet(workbook_path: Path, sheet_name: str) -> dict:
    profile = {"headers": [], "data_rows": 0, "blank_rows": 0}
    for event, _, value in iter_sheet_events(workbook_path, sheet_name):
        if event == "header":
            profile["headers"] = value
        elif event == "blank":
            profile["blank_rows"] += 1
        else:
            profile["data_rows"] += 1
    profile["loaded"] = False
    profile["exclusion_reason"] = (
        "This sheet is at a property-by-FHA-number grain and is not the "
        "property-level dimension."
    )
    return profile


def require_source_files() -> dict[str, Path]:
    paths = {name: RAW_DIR / name for name in SOURCES}
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing source file(s): "
            + ", ".join(missing)
            + ". Run the download command first."
        )
    return paths


def profile_sources() -> tuple[dict, dict[str, Path]]:
    paths = require_source_files()
    retrieved_at = utc_now()
    file_hashes = {name: sha256_file(path) for name, path in paths.items()}

    property_path = paths["active_multifamily_portfolio_20261006.xlsx"]
    property_ids: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    property_numeric_errors: Counter[str] = Counter()
    arkansas_hot_springs = 0

    def collect_property(sheet: str, row_number: int, record: dict[str, str], payload: str):
        nonlocal arkansas_hot_springs
        property_id = record.get("property_id", "").strip()
        if property_id:
            property_ids[property_id] += 1
            try:
                int_value(property_id)
            except (InvalidOperation, ValueError):
                property_numeric_errors["property_id"] += 1
        for field in ("total_unit_count", "total_assisted_unit_count"):
            value = record.get(field, "").strip()
            if value:
                try:
                    int_value(value)
                except (InvalidOperation, ValueError):
                    property_numeric_errors[field] += 1
        state = record.get("state_code", "").strip().upper()
        state_counts[state or "(blank)"] += 1
        if (
            state == "AR"
            and record.get("city_name_text", "").strip().upper() == "HOT SPRINGS"
        ):
            arkansas_hot_springs += 1

    property_csv = PROCESSED_DIR / "raw_hud_active_property.csv"
    property_url = SOURCES["active_multifamily_portfolio_20261006.xlsx"][0]
    property_sheets = workbook_sheet_names(property_path)
    if PROPERTY_SHEET not in property_sheets:
        raise ValueError(f"Expected property sheet {PROPERTY_SHEET!r} was not found.")
    property_profile = extract_workbook(
        property_path,
        (PROPERTY_SHEET,),
        property_csv,
        property_url,
        retrieved_at,
        file_hashes[property_path.name],
        collect_property,
    )
    excluded_property_sheet = next(
        (name for name in property_sheets if name.strip() == EXCLUDED_PROPERTY_SHEET),
        None,
    )
    if excluded_property_sheet is not None:
        property_profile[excluded_property_sheet] = count_excluded_sheet(
            property_path, excluded_property_sheet
        )
    other_property_sheets = [
        name
        for name in property_sheets
        if name not in {PROPERTY_SHEET, excluded_property_sheet}
    ]

    property_key_groups = sum(count > 1 for count in property_ids.values())
    property_duplicate_rows = sum(count - 1 for count in property_ids.values())
    property_id_set = set(property_ids)

    rent_path = paths["contracts_rent_utility_allowance_20261006.xlsx"]
    rent_sheets_in_file = workbook_sheet_names(rent_path)
    missing_rent_sheets = [name for name in RENT_SHEETS if name not in rent_sheets_in_file]
    if missing_rent_sheets:
        raise ValueError(
            "Expected rent worksheet(s) were not found: "
            + ", ".join(missing_rent_sheets)
        )
    rent_rows = 0
    rent_key_counts: Counter[tuple[str, str, str]] = Counter()
    rent_key_payloads: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    rent_key_sheets: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    rent_key_field_values: dict[
        tuple[str, str, str], dict[str, set[str]]
    ] = defaultdict(lambda: defaultdict(set))
    rent_payload_counts: Counter[str] = Counter()
    rent_property_ids: set[str] = set()
    unmatched_rows = 0
    unmatched_property_ids: set[str] = set()
    blank_fields: Counter[str] = Counter()
    numeric_errors: Counter[str] = Counter()
    negative_values: Counter[str] = Counter()
    bedroom_counts: Counter[str] = Counter()

    def collect_rent(sheet: str, row_number: int, record: dict[str, str], payload: str):
        nonlocal rent_rows, unmatched_rows
        rent_rows += 1
        rent_payload_counts[payload] += 1
        property_id = record.get("property_id", "").strip()
        if property_id:
            rent_property_ids.add(property_id)
        else:
            blank_fields["property_id"] += 1
        for field in RENT_HEADERS:
            if not record.get(field, "").strip():
                blank_fields[field] += 1
        key = (
            property_id,
            record.get("contract_number", "").strip(),
            record.get("assistance_bedroom_count", "").strip(),
        )
        rent_key_counts[key] += 1
        rent_key_payloads[key].add(payload)
        rent_key_sheets[key].add(sheet)
        for field in (
            "assistance_unit_count",
            "contract_rent_amount",
            "fair_market_rent_amount",
            "utility_allowance_amount",
        ):
            rent_key_field_values[key][field].add(record.get(field, "").strip())
        if property_id and property_id not in property_id_set:
            unmatched_rows += 1
            unmatched_property_ids.add(property_id)
        bedroom = record.get("assistance_bedroom_count", "").strip()
        bedroom_counts[bedroom or "(blank)"] += 1
        numeric_fields = {
            "property_id": property_id,
            "assistance_bedroom_count": bedroom,
            "assistance_unit_count": record.get("assistance_unit_count", "").strip(),
            "contract_rent_amount": record.get("contract_rent_amount", "").strip(),
            "fair_market_rent_amount": record.get("fair_market_rent_amount", "").strip(),
            "utility_allowance_amount": record.get("utility_allowance_amount", "").strip(),
        }
        for field, value in numeric_fields.items():
            if not value:
                continue
            try:
                parsed = (
                    int_value(value)
                    if field in {
                        "property_id",
                        "assistance_bedroom_count",
                        "assistance_unit_count",
                    }
                    else decimal_value(value)
                )
                if field in {
                    "assistance_unit_count",
                    "contract_rent_amount",
                    "fair_market_rent_amount",
                    "utility_allowance_amount",
                } and parsed < 0:
                    negative_values[field] += 1
            except (InvalidOperation, ValueError):
                numeric_errors[field] += 1

    rent_csv = PROCESSED_DIR / "raw_hud_contract_rent.csv"
    rent_url = SOURCES["contracts_rent_utility_allowance_20261006.xlsx"][0]
    rent_profile = extract_workbook(
        rent_path,
        RENT_SHEETS,
        rent_csv,
        rent_url,
        retrieved_at,
        file_hashes[rent_path.name],
        collect_rent,
    )

    duplicate_key_groups = sum(count > 1 for count in rent_key_counts.values())
    duplicate_key_rows = sum(count - 1 for count in rent_key_counts.values())
    conflicting_key_groups = sum(
        len(payloads) > 1 for payloads in rent_key_payloads.values()
    )
    exact_payload_copy_groups = sum(count > 1 for count in rent_payload_counts.values())
    exact_payload_copy_rows = sum(
        count - 1 for count in rent_payload_counts.values()
    )
    cross_sheet_key_groups = sum(
        len(sheet_names) > 1 for sheet_names in rent_key_sheets.values()
    )
    field_variation_groups = {
        field: sum(
            rent_key_counts[key] > 1
            and len(values.get(field, set())) > 1
            for key, values in rent_key_field_values.items()
        )
        for field in (
            "assistance_unit_count",
            "contract_rent_amount",
            "fair_market_rent_amount",
            "utility_allowance_amount",
        )
    }
    distinct_property_ids = len(property_id_set)
    duplicate_key_message = (
        "One source row per property/contract/bedroom is not supported. "
        "Keep source rows and do not aggregate rent until the missing row "
        "discriminator or source duplication is resolved."
    )

    source_manifest = []
    for filename, (url, source_kind) in SOURCES.items():
        source_manifest.append(
            {
                "filename": filename,
                "source_kind": source_kind,
                "source_url": url,
                "source_as_of_date": (
                    SOURCE_AS_OF.isoformat()
                    if source_kind in {"property_workbook", "rent_workbook"}
                    else None
                ),
                "retrieved_at_utc": retrieved_at,
                "bytes": paths[filename].stat().st_size,
                "sha256": file_hashes[filename],
            }
        )

    profile = {
        "profile_schema": "hud-source-profile-v1",
        "generated_at_utc": retrieved_at,
        "source_as_of_date": SOURCE_AS_OF.isoformat(),
        "sources": source_manifest,
        "property_workbook": {
            "filename": property_path.name,
            "sha256": file_hashes[property_path.name],
            "loaded_sheet": PROPERTY_SHEET,
            "sheets": property_profile,
            "other_unmodeled_sheets": other_property_sheets,
            "property_rows": sum(
                item["data_rows"]
                for name, item in property_profile.items()
                if name == PROPERTY_SHEET
            ),
            "distinct_nonblank_property_ids": distinct_property_ids,
            "blank_property_ids": (
                property_profile[PROPERTY_SHEET]["data_rows"]
                - sum(property_ids.values())
            ),
            "duplicate_property_id_groups": property_key_groups,
            "duplicate_property_id_rows": property_duplicate_rows,
            "arkansas_property_rows": state_counts.get("AR", 0),
            "arkansas_hot_springs_city_rows": arkansas_hot_springs,
            "state_code_row_counts": dict(sorted(state_counts.items())),
            "numeric_parse_errors": dict(property_numeric_errors),
        },
        "rent_workbook": {
            "filename": rent_path.name,
            "sha256": file_hashes[rent_path.name],
            "loaded_sheets": list(RENT_SHEETS),
            "sheets": rent_profile,
            "nonblank_source_rows": rent_rows,
            "distinct_property_ids": len(rent_property_ids),
            "blank_source_fields": dict(blank_fields),
            "numeric_parse_errors": dict(numeric_errors),
            "negative_amount_or_count_rows": dict(negative_values),
            "bedroom_count_row_counts": dict(sorted(bedroom_counts.items())),
            "stated_key": [
                "property_id",
                "contract_number",
                "assistance_bedroom_count",
            ],
            "stated_key_unique_groups": len(rent_key_counts) - duplicate_key_groups,
            "stated_key_duplicate_groups": duplicate_key_groups,
            "stated_key_excess_rows": duplicate_key_rows,
            "stated_key_conflicting_payload_groups": conflicting_key_groups,
            "cross_sheet_stated_key_groups": cross_sheet_key_groups,
            "stated_key_field_variation_groups": field_variation_groups,
            "exact_payload_copy_groups": exact_payload_copy_groups,
            "exact_payload_copy_rows": exact_payload_copy_rows,
            "property_match_rows": rent_rows - unmatched_rows,
            "property_unmatched_rows": unmatched_rows,
            "property_unmatched_distinct_ids": len(unmatched_property_ids),
            "grain_status": "unresolved",
            "grain_note": duplicate_key_message,
        },
        "gates": {
            "property_id_populated_and_unique": (
                "pass"
                if property_key_groups == 0
                and sum(property_ids.values())
                == sum(
                    item["data_rows"]
                    for name, item in property_profile.items()
                    if name == PROPERTY_SHEET
                )
                else "fail"
            ),
            "rent_workbook_sheet_schemas_match": (
                "pass"
                if all(
                    rent_profile[name]["headers"] == RENT_HEADERS
                    for name in RENT_SHEETS
                )
                else "fail"
            ),
            "property_contract_bedroom_grain": "blocked",
            "rent_property_join": (
                "partial"
                if unmatched_rows
                else "complete"
            ),
            "rent_aggregation": "blocked",
        },
    }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    profile_path = ARTIFACT_DIR / "source-profile-2026-11-05.json"
    profile_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return profile, {
        "property_csv": property_csv,
        "rent_csv": rent_csv,
        "profile_json": profile_path,
    }


def print_profile_summary(profile: dict, output_path: Path) -> None:
    properties = profile["property_workbook"]
    rents = profile["rent_workbook"]
    print(f"Wrote source profile: {output_path.relative_to(ROOT)}")
    print(
        "Property sheet: "
        f"{properties['property_rows']:,} rows; "
        f"{properties['distinct_nonblank_property_ids']:,} distinct IDs; "
        f"{properties['duplicate_property_id_groups']:,} duplicate ID groups."
    )
    print(
        "Rent sheets: "
        f"{rents['nonblank_source_rows']:,} source rows; "
        f"{rents['stated_key_excess_rows']:,} excess rows on the proposed key; "
        f"{rents['property_unmatched_rows']:,} unmatched to the property sheet."
    )
    print("Rent grain status: unresolved; no rent aggregation was generated.")


def psql_command(*, sql_text: str | None = None, copy_table: str | None = None, csv_path: Path | None = None) -> None:
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "psql",
        "--no-psqlrc",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        "portfolio",
        "-d",
        "portfolio",
    ]
    if copy_table is not None:
        if csv_path is None:
            raise ValueError("A CSV file is required for a COPY operation.")
        copy_columns = ", ".join(RAW_CSV_HEADERS)
        command.extend(
            [
                "-c",
                f"\\copy {copy_table} ({copy_columns}) FROM STDIN WITH (FORMAT csv, HEADER true)",
            ]
        )
        input_bytes = csv_path.read_bytes()
    elif sql_text is not None:
        input_bytes = sql_text.encode("utf-8")
    else:
        raise ValueError("Provide SQL text or a COPY source.")
    subprocess.run(command, cwd=ROOT, input=input_bytes, check=True)


def load_database(profile: dict, csv_paths: dict[str, Path]) -> None:
    if profile["gates"]["property_id_populated_and_unique"] != "pass":
        raise RuntimeError("The property primary-key gate did not pass; database load stopped.")
    if profile["gates"]["rent_workbook_sheet_schemas_match"] != "pass":
        raise RuntimeError("The rent worksheet schema gate did not pass; database load stopped.")
    if profile["rent_workbook"]["blank_source_fields"]:
        raise RuntimeError(
            "The rent source has blank required fields: "
            f"{profile['rent_workbook']['blank_source_fields']}. "
            "Resolve them before typed loading."
        )
    for source_name, errors in (
        ("property", profile["property_workbook"]["numeric_parse_errors"]),
        ("rent", profile["rent_workbook"]["numeric_parse_errors"]),
    ):
        if errors:
            raise RuntimeError(
                f"The {source_name} source has numeric parse errors: {errors}. "
                "Resolve them before typed loading."
            )

    schema_sql = (ROOT / "sql" / "001_schema.sql").read_text(encoding="utf-8")
    model_sql = (ROOT / "sql" / "002_build_model.sql").read_text(encoding="utf-8")
    psql_command(sql_text=schema_sql)
    psql_command(
        sql_text=(
            "TRUNCATE TABLE raw.hud_active_property, raw.hud_contract_rent "
            "RESTART IDENTITY;"
        )
    )
    psql_command(
        copy_table="raw.hud_active_property",
        csv_path=csv_paths["property_csv"],
    )
    psql_command(
        copy_table="raw.hud_contract_rent",
        csv_path=csv_paths["rent_csv"],
    )
    psql_command(sql_text=model_sql)
    psql_command(
        sql_text=(
            "SELECT 'properties=' || COUNT(*) FROM core.dim_hud_property;\n"
            "SELECT 'rent_observations=' || COUNT(*) "
            "FROM core.hud_rent_observation;\n"
            "SELECT 'unmatched_rent_observations=' || "
            "unmatched_rent_observation_rows "
            "FROM mart.vw_hud_source_quality;\n"
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile HUD public workbooks and load the local PostgreSQL demo model."
    )
    parser.add_argument(
        "command", choices=("download", "profile", "load"), help="Action to run."
    )
    args = parser.parse_args()

    try:
        if args.command == "download":
            download_sources()
            return 0
        profile, csv_paths = profile_sources()
        profile_path = csv_paths["profile_json"]
        print_profile_summary(profile, profile_path)
        if args.command == "load":
            load_database(profile, csv_paths)
            print("Loaded the source, staging, core, and mart layers in local PostgreSQL.")
        return 0
    except (FileNotFoundError, OSError, ValueError, InvalidOperation, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

