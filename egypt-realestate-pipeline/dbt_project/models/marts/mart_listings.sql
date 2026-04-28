with base as (
    select * from {{ ref('stg_listings') }}
),

pivoted as (
    select
        year,
        max(case when indicator_key = 'cpi'
            then value end)               as cpi,
        max(case when indicator_key = 'inflation'
            then value end)               as inflation_rate,
        max(case when indicator_key = 'gdp_per_capita'
            then value end)               as gdp_per_capita_usd,
        max(case when indicator_key = 'real_interest_rate'
            then value end)               as real_interest_rate,
        max(case when indicator_key = 'urban_population'
            then value end)               as urban_population
    from base
    group by year
),

enriched as (
    select
        year,
        round(cpi, 2)                                    as cpi,
        round(inflation_rate, 2)                         as inflation_rate_pct,
        round(gdp_per_capita_usd, 2)                     as gdp_per_capita_usd,
        round(real_interest_rate, 2)                     as real_interest_rate_pct,
        round(urban_population)                          as urban_population,

        -- affordability proxy: higher inflation + higher rates = worse affordability
        case
            when inflation_rate > 20 then 'very_poor'
            when inflation_rate > 10 then 'poor'
            when inflation_rate > 5  then 'moderate'
            else 'good'
        end                                              as affordability_rating,

        -- year over year gdp growth
        round(
            (gdp_per_capita_usd - lag(gdp_per_capita_usd)
                over (order by year)) /
            nullif(lag(gdp_per_capita_usd)
                over (order by year), 0) * 100
        , 2)                                             as gdp_growth_pct

    from pivoted
    where cpi is not null
)

select * from enriched
order by year desc