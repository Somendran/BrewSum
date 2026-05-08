select
    brewery_id,
    count(*) as brewery_count
from {{ ref('int_breweries_cleaned') }}
group by brewery_id
having count(*) > 1
