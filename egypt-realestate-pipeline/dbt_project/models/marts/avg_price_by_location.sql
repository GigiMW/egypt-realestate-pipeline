with base as (
    select * from {{ ref('stg_listings') }}
),

by_location as (
    select
        location,
        count(*) as listing_count,
        round(avg(price_egp), 2) as avg_price_egp,
        round(avg(price_per_sqm_egp), 2) as avg_price_per_sqm_egp,
        round(min(price_egp), 2) as min_price_egp,
        round(max(price_egp), 2) as max_price_egp
    from base
    group by location
)

select * from by_location
order by listing_count desc, avg_price_per_sqm_egp desc