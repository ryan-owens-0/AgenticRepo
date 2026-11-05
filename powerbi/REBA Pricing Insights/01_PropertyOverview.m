let
    Source = PostgreSQL.Database("127.0.0.1:5432", "portfolio", [CreateNavigationProperties=false]),
    PropertyOverview = Value.NativeQuery(Source, "SELECT state_code, state_name, county_name, msa_name, property_category, hud_property_count, hud_reported_total_units, hud_reported_assisted_units FROM mart.vw_hud_property_overview", null, [EnableFolding=true])
in
    PropertyOverview
