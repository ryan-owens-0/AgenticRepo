# REBA Reports and Dashboards Manager — reporting workback

This portfolio slice is scoped to the Manager posting's hands-on reporting responsibilities: iterate on a standard Power BI offering, build custom reports, and represent reporting and customer needs in model and metric design. It deliberately treats data pipelines and production engineering as supporting context rather than evidence for this role. [REBA Manager posting](https://www.getreba.com/career/reports-and-dashboards-manager-reba-bi/)

## What this project can demonstrate

| Role responsibility | Portfolio evidence | Current status and boundary |
|---|---|---|
| Build and iterate on an out-of-the-box Power BI offering | `C:\Users\aries\Documents\REBAtest.pbix`; Power Query query definitions in `powerbi/REBA Pricing Insights/` | One imported model and one report page are present. The page shows HUD portfolio coverage and source-readiness diagnostics. It is an in-progress prototype, not a polished production offering. |
| Own custom and complex Power BI reports | `powerbi/REBA Pricing Insights/Report Layout.md` | Defines a portfolio coverage page and a rent-source readiness page, with audience-facing filters and detail. Only the first page has been built in the PBIX so far. |
| Build paginated reports | `reports/HUD Pricing Inputs - Portfolio and Data Quality Review.rdl` | Editable RDL authored with source-quality summary and state/category detail. XML structure has been inspected; it has not been opened or previewed in Report Builder. The separate ODBC smoke-test preview only proved the connection path, not this RDL. |
| Represent customers in model and metric design | `powerbi/REBA Pricing Insights/Measures.dax`, `semantics/hud_multifamily_ossie.yaml`, `semantics/mapping-ledger.csv`, and the grain safeguards below | Metrics are limited to counts and data-quality rates whose grain is supported. HUD extracts do not contain customer-specific semantics or private-market operating data. |

## Report and metric design decisions

- **Portfolio coverage:** count HUD properties and HUD-reported total/assisted units from the non-overlapping property overview groups. Keep filters aligned to state, county/MSA, and HUD property category.
- **Rent-source readiness:** count source observations and report unmatched-property rows, repeated proposed-key rows, conflicting payload rows, exact-copy groups, and unmatched-row rate. Label these as source diagnostics.
- **Paginated output:** use a fixed letter page with a concise source-quality summary followed by a state/category portfolio table. The detail should support print/export and customer service follow-up; it must retain source-date and unit-count caveats.
- **No pricing measure:** contract rent, FMR, and utility allowance remain row-level values. Repeated keys contain conflicting payloads, so averages, totals, weighted rents, and recommendations would be unsupported.
- **No false market comparison:** FMR is a HUD program benchmark and contract rent comes from HUD program files. Neither represents live asking-rent comps, concessions, occupancy, leasing velocity, renewals, realized revenue, or NOI.

## Readiness against the posting

- Demonstrated in this project: public-source model design; additive count metrics at explicit grains; data-quality diagnostics; Power BI import and report authoring; editable paginated-report definition; careful limitations in the report narrative.
- Still needed to make the artifacts review-ready: complete and format the DAX measures in the PBIX, build the second report page, open and preview the authored RDL, and capture a clean screenshot or PDF of each finished deliverable.
- Not evidenced by these artifacts: five years of BI tenure, advanced proficiency from a sustained customer workload, prior production Report Builder use, or leading/coaching a reporting team. Those require separate experience evidence and should not be implied by a new portfolio exercise.

## Next build sequence

1. Finish the Power BI semantic measures and replace the raw wide source summary with titled KPI cards and a ranked state visual.
2. Add the rent-source readiness page with match-status/state and bedroom breakdowns plus a diagnostic detail table.
3. Open the RDL in Report Builder, resolve any parameter/data-source prompts, preview both datasets, and adjust pagination and labels based on the rendered output.
4. Save the PBIX and RDL alongside a PDF or screenshots and record what was actually previewed.

