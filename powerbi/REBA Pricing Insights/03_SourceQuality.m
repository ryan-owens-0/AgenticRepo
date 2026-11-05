let
    Source = PostgreSQL.Database("127.0.0.1:5432", "portfolio", [CreateNavigationProperties=false]),
    SourceQuality = Value.NativeQuery(Source, "SELECT hud_property_rows, hud_rent_observation_rows, unmatched_rent_observation_rows, nonunique_property_contract_bedroom_key_groups, exact_payload_copy_groups FROM mart.vw_hud_source_quality", null, [EnableFolding=true])
in
    SourceQuality
