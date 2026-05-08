with ranked as (
    select
        *,
        row_number() over (
            partition by brewery_id
            order by ingestion_timestamp desc, loaded_at desc
        ) as brewery_rank
    from {{ ref('stg_breweries') }}
    where lower(trim(country)) = 'united states'
),

deduplicated as (
    select
        brewery_id,
        brewery_name,
        lower(trim(brewery_type)) as brewery_type,
        address_1,
        address_2,
        address_3,
        city,
        state_province,
        postal_code,
        country,
        longitude,
        latitude,
        phone,
        website_url,
        deprecated_state,
        deprecated_street,
        ingestion_timestamp,
        loaded_at,
        latitude is not null and longitude is not null as has_coordinates
    from ranked
    where brewery_rank = 1
)

select *
from deduplicated
