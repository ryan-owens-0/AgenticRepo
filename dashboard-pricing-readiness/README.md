# Pricing data foundation dashboard

A responsive HTML dashboard of HUD multifamily portfolio coverage and rent-source readiness. The dashboard contains 37,438 property records, 3,022,278 HUD-reported units, 73,298 rent-source rows, state and bedroom charts, and repeated-key diagnostics. The unmatched-row rate is 9,935 / 73,298 (13.6%); the conflicting-group rate is 27,741 / 28,351 repeated groups (97.8%). These rates use different denominators.

## View immediately

Download `../deliverables/HUD-Pricing-Data-Foundation.html` and open it in a browser for the portable offline snapshot. The HTML includes its reviewed data.

For a local HTTP preview, run from the repository root:

```powershell
py -3 -m http.server 8765 --bind 127.0.0.1 --directory dashboard-pricing-readiness/dist
```

Open http://127.0.0.1:8765. Keep every file in `dist` together: `index.html` fetches its content-addressed JSON sidecar. The build manifest records hashes for reproducibility.

## Edit and rebuild

App-specific UI and CSS live in `src/content/dashboard/`. Reviewed data and provenance live in `src/data.json`. Read `AGENTS.md` before editing. The checked-in source includes the shared runtime and pinned package lock.

The verified build in this revision used the installed Data analytics plugin's `scripts/data-app.mjs build --project-dir <dashboard-directory> --separate-data`, followed by `export-offline`. The plugin build requires no project dependency installation. Its offline export lives under `.data-app-offline/exports/`; the delivered HTML is copied to the repository's `deliverables/` folder.

## Evidence and limits

HUD source date: October 6, 2026. Capture date: November 5, 2026. Values are a saved reviewed snapshot; opening the HTML does not query PostgreSQL or refresh HUD data. Card menus retain source inspection, data copying, and chart exports.

Property counts and source-reported units use the property extract. Rent observations retain both workbook sheets and duplicate diagnostics. The proposed property / contract / bedroom key repeats with conflicting values, so rent totals, averages, and pricing recommendations are not published. The snapshot lacks live asking rents, concessions, occupancy and leasing velocity.

The final build passed authored-content/runtime verification. A browser review confirmed chart rendering, displayed metrics, responsive narrow layout, and the state chart's source-inspection panel. PDF export and every menu destination were not exercised.
