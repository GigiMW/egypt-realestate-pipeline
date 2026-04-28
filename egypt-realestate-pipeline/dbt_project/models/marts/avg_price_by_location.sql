with base as (
    select * from {{ ref('stg_listings') }}
),

by_indicator as (
    select
        indicator_key,
        indicator_name,
        count(*)                as total_years,
        round(min(value), 2)    as min_value,
        round(max(value), 2)    as max_value,
        round(avg(value), 2)    as avg_value,
        min(year)               as earliest_year,
        max(year)               as latest_year
    from base
    group by indicator_key, indicator_name
)

select * from by_indicator