let
    Source = PostgreSQL.Database("127.0.0.1:5432", "portfolio", [CreateNavigationProperties=false]),
    RentQuality = Value.NativeQuery(Source, "SELECT property_match_status, state_code, assistance_bedroom_count, COUNT(*) AS source_row_count, COUNT(*) FILTER (WHERE stated_key_row_count > 1) AS repeated_key_rows, COUNT(*) FILTER (WHERE stated_key_row_count > 1 AND stated_key_distinct_payload_count > 1) AS conflicting_payload_rows, COUNT(*) FILTER (WHERE exact_payload_copy_count > 1) AS exact_payload_copy_rows FROM mart.vw_hud_rent_observation GROUP BY property_match_status, state_code, assistance_bedroom_count ORDER BY property_match_status, state_code, assistance_bedroom_count", null, [EnableFolding=true])
in
    RentQuality
