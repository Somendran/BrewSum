select
    state_province as state,
    count(*) as total_breweries,
    countif(brewery_type = 'micro') as micro_breweries,
    countif(brewery_type = 'nano') as nano_breweries,
    countif(brewery_type = 'regional') as regional_breweries,
    countif(brewery_type = 'brewpub') as brewpub_breweries,
    countif(brewery_type = 'large') as large_breweries,
    countif(brewery_type = 'planning') as planning_breweries,
    countif(brewery_type = 'bar') as bar_breweries,
    countif(brewery_type = 'contract') as contract_breweries,
    countif(brewery_type = 'proprietor') as proprietor_breweries,
    countif(brewery_type = 'closed') as closed_breweries,
    round(
        100 * safe_divide(
            countif(website_url is not null and trim(website_url) != ''),
            count(*)
        ),
        2
    ) as pct_with_websites,
    round(
        100 * safe_divide(countif(has_coordinates), count(*)),
        2
    ) as pct_with_coordinates
from {{ ref('int_breweries_cleaned') }}
where state_province is not null
group by state
