-- How prices move over time: one row per scrape date and area.
-- 'All areas' rows give the market-wide figure for each date.

with base as (
    select * from {{ ref('int_listings_with_area') }}
),

stats as (
    select
        snapshot_date,
        coalesce(area, 'All areas') as area,
        count(*) as listing_count,
        round(avg(price_egp), 2) as avg_price_egp,
        round(avg(price_per_sqm_egp), 2) as avg_price_per_sqm_egp,
        round(median(price_per_sqm_egp), 2) as median_price_per_sqm_egp
    from base
    group by grouping sets ((snapshot_date, area), (snapshot_date))
)

select
    *,
    -- change in median EGP/sqm vs. the previous snapshot for the same area
    round(
        median_price_per_sqm_egp
        - lag(median_price_per_sqm_egp) over (partition by area order by snapshot_date),
        2
    ) as median_price_per_sqm_change_egp
from stats
order by snapshot_date desc, area = 'All areas' desc, listing_count desc
