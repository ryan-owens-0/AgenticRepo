# REBA Pricing Insights — Power BI page plan

## Page 1 — Portfolio coverage
- Cards: HUD properties; HUD reported units; HUD reported assisted units.
- Horizontal bar: property count by state (descending; use state name and HUD Properties).
- Matrix: state, county, property category; HUD property count and reported unit counts.
- Slicers: state, property category.

## Page 2 — Rent source readiness
- Cards: rent source rows; unmatched source rows; unmatched row rate; repeated proposed-key rows; conflicting payload rows.
- Stacked bar: rent source rows by property match status and state.
- Column chart: source rows by assistance bedroom count, split by match status.
- Detail table: state, property match status, bedroom count, row counts and duplicate-key diagnostic counts.

## Semantic safeguards
- `PropertyOverview` is already aggregated at nonoverlapping location/category groups; sum its property/unit counts only across its current filtered group set.
- `RentSourceQuality` is grouped at match status/state/bedroom grain. Its counts are additive across those groups.
- Do not load `contract_rent_amount`, `fair_market_rent_amount`, `utility_allowance_amount`, or `row_gross_amount` as additive values. Do not publish averages or pricing recommendations.
- The dashboard echoes REBA's portfolio and pricing-readiness ideas using public HUD data. It does not measure private market asking rents, occupancy, lease velocity, concessions, renewals, realized revenue, or recommended prices.

## Connect
The Power Query scripts use Power BI's native PostgreSQL connector. Configure credentials in Power BI Desktop for `127.0.0.1:5432`, database `portfolio`, using the local database account. No credential is stored in these files.
