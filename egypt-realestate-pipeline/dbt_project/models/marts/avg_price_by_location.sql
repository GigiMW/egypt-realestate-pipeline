with base as (
    select * from {{ ref('mart_listings') }}
    where location is not null
      and price_egp is not null
      and area_sqm is not null
)

select
    location,
    count(*)                        as total_listings,
    round(avg(price_egp))           as avg_price_egp,
    round(avg(price_per_sqm))       as avg_price_per_sqm,
    round(min(price_egp))           as min_price_egp,
    round(max(price_egp))           as max_price_egp,
    sum(case when is_value_listing
        then 1 else 0 end)          as value_listings_count
from base
group by location
having count(*) >= 2
order by avg_price_per_sqm desc