with base as (
    select * from {{ ref('stg_listings') }}
),

categorized as (
    select
        case
            when price_egp < 3000000 then 'under_3m'
            when price_egp < 5000000 then '3m_to_5m'
            when price_egp < 10000000 then '5m_to_10m'
            else '10m_plus'
        end as price_bucket,
        count(*) as listing_count,
        round(avg(price_egp), 2) as avg_price_egp,
        round(avg(price_per_sqm_egp), 2) as avg_price_per_sqm_egp
    from base
    group by 1
)

select * from categorized
order by listing_count desc, price_bucket