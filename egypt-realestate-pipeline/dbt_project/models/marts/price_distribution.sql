with base as (
    select * from {{ ref('stg_listings') }}
    where indicator_key = 'inflation'
),

categorized as (
    select
        year,
        value                           as inflation_rate,
        case
            when value < 5  then 'low'
            when value < 10 then 'moderate'
            when value < 20 then 'high'
            else 'very_high'
        end                             as inflation_category,
        case
            when value < 5  then 1
            when value < 10 then 2
            when value < 20 then 3
            else 4
        end                             as severity_rank
    from base
)

select * from categorized
order by year desc