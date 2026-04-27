with base as (
    select * from {{ ref('mart_listings') }}
    where price_egp is not null
)

select
    price_bucket,
    count(*)                  as listing_count,
    round(avg(price_egp))     as avg_price_egp,
    round(avg(price_per_sqm)) as avg_price_per_sqm,
    round(min(price_egp))     as min_price_egp,
    round(max(price_egp))     as max_price_egp
from base
group by price_bucket
order by avg_price_egp asc