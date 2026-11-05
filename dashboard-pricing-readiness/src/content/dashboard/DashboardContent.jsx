import React from "react";
import {
  DataComponent, EvidenceChart, Section, SectionHeader, useDataApp,
} from "../../data-app-public.jsx";
import "./dashboard.css";

const statesSpec = {
  type: "horizontalBar",
  x: "state",
  y: "properties",
  xLabel: "HUD property records",
  showXAxisLabel: false,
  valueDecimals: 0,
};

const bedroomSpec = {
  type: "bar",
  x: "bedrooms",
  y: "sourceRows",
  xLabel: "Assistance bedroom count",
  showXAxisLabel: false,
  valueDecimals: 0,
};

function Metric({ id, label, value, detail, queryId, rows }) {
  return <DataComponent variant="card" className="metric-card" id={id} title={label}
    queryId={queryId} displayRows={rows} sourceRows={rows}>
    <div className="metric-value">{value}</div>
    <div className="metric-detail">{detail}</div>
  </DataComponent>;
}

export function DashboardContent() {
  const { reviewedRows } = useDataApp();
  const portfolio = reviewedRows("portfolio_summary")[0] ?? {};
  const quality = reviewedRows("rent_quality")[0] ?? {};
  const stateRows = reviewedRows("state_property_counts");
  const bedroomRows = reviewedRows("bedroom_source_rows");
  const propertyRows = reviewedRows("portfolio_summary");
  const rentRows = reviewedRows("rent_quality");
  const unmatchedShare = quality.rentRows ? quality.unmatchedRows / quality.rentRows : 0;
  const conflictShare = quality.duplicateKeyGroups ? quality.conflictingGroups / quality.duplicateKeyGroups : 0;

  return <div className="pricing-dashboard">
    <header className="pricing-header">
      <div>
        <p className="eyebrow">HUD multifamily public data · Snapshot 06 Oct 2026</p>
        <h1>Pricing data foundation</h1>
        <p className="header-copy">Portfolio coverage and rent-source quality from HUD public records. Review the source coverage, then the data issues that need resolution before rent analysis.</p>
      </div>
      <div className="status-pill"><span /> Captured 05 Nov 2026</div>
    </header>

    <SectionHeader id="portfolio-scope-heading" title="Portfolio coverage" />
    <Section columns={4} spacing="none">
      <Metric id="property-records" label="HUD properties" value={Number(portfolio.propertyRows ?? 0).toLocaleString()}
        detail="Unique property IDs in the active multifamily sheet" queryId="portfolio_summary" rows={propertyRows} />
      <Metric id="hud-units" label="HUD reported units" value={Number(portfolio.hudReportedUnits ?? 0).toLocaleString()}
        detail="Source-reported total unit count; not an occupancy measure" queryId="portfolio_summary" rows={propertyRows} />
      <Metric id="rent-observations" label="Rent source rows" value={Number(quality.rentRows ?? 0).toLocaleString()}
        detail="Nonblank rows retained from both workbook sheets" queryId="rent_quality" rows={rentRows} />
      <Metric id="unmatched-rent" label="Unmatched rent rows" value={`${(unmatchedShare * 100).toFixed(1)}%`}
        detail={`${Number(quality.unmatchedRows ?? 0).toLocaleString()} rows have no property-sheet match`}
        queryId="rent_quality" rows={rentRows} />
    </Section>

    <SectionHeader id="pricing-readiness-heading" title="Pricing data readiness" />
    <Section columns={2} spacing="none">
      <EvidenceChart variant="card" padding="spacious" id="property-state-coverage"
        title="Top 12 states by HUD property count" queryId="state_property_counts"
        spec={statesSpec} rows={stateRows} sourceRows={stateRows} height={320} />
      <EvidenceChart variant="card" padding="spacious" id="bedroom-observations"
        title="Rent source rows by assistance bedroom count" queryId="bedroom_source_rows"
        spec={bedroomSpec} rows={bedroomRows} sourceRows={bedroomRows} height={320} />
    </Section>

    <SectionHeader id="quality-gates-heading" title="Data quality gates" />
    <Section columns={3} spacing="none">
      <Metric id="repeated-keys" label="Repeated property / contract / bedroom groups"
        value={Number(quality.duplicateKeyGroups ?? 0).toLocaleString()}
        detail="Groups with more than one row for the proposed property / contract / bedroom key"
        queryId="rent_quality" rows={rentRows} />
      <Metric id="conflicting-keys" label="Conflicting repeated groups"
        value={`${(conflictShare * 100).toFixed(1)}%`}
        detail={`${Number(quality.conflictingGroups ?? 0).toLocaleString()} of ${Number(quality.duplicateKeyGroups).toLocaleString()} repeated groups have differing payloads`}
        queryId="rent_quality" rows={rentRows} />
      <Metric id="exact-copies" label="Exact cross-sheet copy groups"
        value={Number(quality.exactCopyGroups ?? 0).toLocaleString()}
        detail="Preserved and flagged; no deduplication rule assumed"
        queryId="rent_quality" rows={rentRows} />
    </Section>

    <section className="pricing-callout" aria-label="Current decision boundary">
      <div className="gate-icon">!</div>
      <div><h2>Resolve the observation grain before rent analysis</h2>
        <p>The HUD files provide contract rent, utility allowance and FMR fields, but the proposed rent-row key repeats with conflicting values. Confirm the missing row discriminator and a documented aggregation rule before calculating rent metrics. Live asking rents, leasing velocity and concessions are absent from this snapshot.</p>
      </div>
      <span className="gate-state">Rent aggregation on hold</span>
    </section>
    <footer className="pricing-provenance">
      <span>HUD source as of <strong>06 Oct 2026</strong> · Captured <strong>05 Nov 2026</strong></span>
      <span>Source rows are observations; they are not a count of unique rental units.</span>
      <a href="https://www.hud.gov/hud-partners/multifamily-preservation" target="_blank" rel="noreferrer">HUD dataset documentation ↗</a>
    </footer>
  </div>;
}
