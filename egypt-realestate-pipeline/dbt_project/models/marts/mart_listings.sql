with base as (
    select * from {{ ref('stg_listings') }}
)

select
    title,
    location,
    price_raw,
    price_egp,
    area_sqm,
    area_sqm_value,
    price_per_sqm_egp,
    bedrooms,
    bathrooms,
    url,
    scraped_at,
    page,
    case
        when price_egp < 3000000 then 'under_3m'
        when price_egp < 5000000 then '3m_to_5m'
        when price_egp < 10000000 then '5m_to_10m'
        else '10m_plus'
    end as price_bucket
from base
order by scraped_at desc