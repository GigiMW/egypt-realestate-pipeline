with base as (
    select * from {{ ref('stg_listings') }}
    where price_egp is not null
      and area_sqm is not null
      and area_sqm > 0
),

enriched as (
    select
        title,
        location,
        price_egp,
        area_sqm,
        url,
        scraped_at,

        -- price per square meter
        round(price_egp / area_sqm) as price_per_sqm,

        -- bucket by price range
        case
            when price_egp < 1000000  then 'under_1M'
            when price_egp < 3000000  then '1M_to_3M'
            when price_egp < 5000000  then '3M_to_5M'
            when price_egp < 10000000 then '5M_to_10M'
            else 'above_10M'
        end as price_bucket,

        -- budget flag
        case
            when round(price_egp / area_sqm) < 50000 then true
            else false
        end as is_value_listing

    from base
)

select * from enriched
order by price_per_sqm asc