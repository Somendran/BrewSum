with source as (
    select *
    from {{ source('raw', 'breweries') }}
),

renamed as (
    select
        cast(id as string) as brewery_id,
        cast(name as string) as brewery_name,
        lower(cast(brewery_type as string)) as brewery_type,
        cast(address_1 as string) as address_1,
        cast(address_2 as string) as address_2,
        cast(address_3 as string) as address_3,
        cast(city as string) as city,
        cast(state_province as string) as state_province,
        cast(postal_code as string) as postal_code,
        cast(country as string) as country,
        safe_cast(longitude as float64) as longitude,
        safe_cast(latitude as float64) as latitude,
        cast(phone as string) as phone,
        cast(website_url as string) as website_url,
        cast(state as string) as deprecated_state,
        cast(street as string) as deprecated_street,
        safe_cast(ingestion_timestamp as timestamp) as ingestion_timestamp,
        current_timestamp() as loaded_at
    from source
    where name is not null
)

select *
from renamed
