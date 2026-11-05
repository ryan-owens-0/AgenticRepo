# Source register

Capture date: 2026-11-05. Source-data as-of date: 2026-10-06.

| Source | Downloaded filename | Modeled sheet(s) | Notes |
|---|---|---|---|
| HUD Active Multifamily Portfolio, property level | active_multifamily_portfolio_20261006.xlsx | Step_01_Property_Level_data | 37,438 nonblank data rows. Property ID is unique in this sheet. The workbook's separate FHA-number sheet has a different grain and is not used in the property dimension. |
| HUD Contracts with Rent Amount and Utility Allowance Amount | contracts_rent_utility_allowance_20261006.xlsx | Contracts_with_Rent_amt_and_Uti; Contracts_w_Rent_amt_and_Uti -2 | Both sheets have the same seven headers. They contain 73,298 nonblank rows in total. The property/contract/bedroom combination is not unique; do not collapse it. |
| HUD Active Multifamily Property DED | active_multifamily_property_ded_2010.pdf | Reference only | The PDF says current as of July 2010. Treat it as historical metadata; read current headers from the workbook. |
| HUD contract rent and utility allowance DED | contract_rent_utility_allowance_ded.pdf | Reference only | Describes property ID, contract number, bedroom group, assistance-unit count, contract rent, FMR, and utility allowance. Verify metric grain against the workbook before aggregating. |

HUD describes these files as compiled from multiple sources and not complete or all-inclusive. They represent a public HUD multifamily universe, not private property-management systems or the whole rental market.

The source URLs and SHA-256 values for the current capture are recorded in artifacts/source-profile-2026-11-05.json.

