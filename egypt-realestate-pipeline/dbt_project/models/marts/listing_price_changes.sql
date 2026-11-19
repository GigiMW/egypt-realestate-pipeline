-- Price history per listing: first vs. latest asking price for every ad
-- seen in more than one snapshot. Negative change = price drop.

with base as (
    select * from {{ ref('int_listings_with_area') }}
),

per_listing as (
    select
        url,
        arg_max(title, snapshot_date) as title,
        arg_max(area, snapshot_date) as area,
        count(*) as snapshots_seen,
        min(snapshot_date) as first_seen,
        max(snapshot_date) as last_seen,
        arg_min(price_egp, snapshot_date) as first_price_egp,
        arg_max(price_egp, snapshot_date) as latest_price_egp
    from base
    group by url
    having count(*) > 1
)

select
    *,
    latest_price_egp - first_price_egp as price_change_egp,
    round(100.0 * (latest_price_egp - first_price_egp) / nullif(first_price_egp, 0), 2) as price_change_pct
from per_listing
order by price_change_pct
