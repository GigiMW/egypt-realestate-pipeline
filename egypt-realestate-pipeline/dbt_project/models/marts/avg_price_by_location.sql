-- Price statistics per area for the most recent scrape (see int_listings_with_area for how areas are mapped).

with base as (
    select * from {{ ref('int_listings_with_area') }}
    where snapshot_date = (select max(snapshot_date) from {{ ref('int_listings_with_area') }})
),

by_area as (
    select
        area,
        count(*) as listing_count,
        round(avg(price_egp), 2) as avg_price_egp,
        round(avg(price_per_sqm_egp), 2) as avg_price_per_sqm_egp,
        round(median(price_per_sqm_egp), 2) as median_price_per_sqm_egp,
        round(min(price_egp), 2) as min_price_egp,
        round(max(price_egp), 2) as max_price_egp
    from base
    group by area
)

select * from by_area
order by listing_count desc, avg_price_per_sqm_egp desc
