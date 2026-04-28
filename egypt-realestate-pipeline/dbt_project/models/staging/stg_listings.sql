with source as (
    select * from raw_indicators
),

cleaned as (
    select
        indicator_key,
        indicator_code,
        indicator_name,
        country,
        country_code,
        year,
        value,
        unit,
        cast(scraped_at as timestamp) as scraped_at
    from source
    where value is not null
      and year >= 1990
)

select * from cleaned