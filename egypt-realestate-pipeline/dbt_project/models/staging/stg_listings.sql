with source as (
    select * from raw_listings
),

cleaned as (
    select
        title,
        location,
        url,
        scraped_at,
        page,

        -- clean price: strip "EGP", commas, spaces → cast to number
        try_cast(
            regexp_replace(price_raw, '[^0-9]', '', 'g')
        as bigint) as price_egp,

        -- clean area: extract first number found
        try_cast(
            regexp_replace(area_sqm, '[^0-9]', '', 'g')
        as integer) as area_sqm

    from source
    where title is not null
)

select * from cleaned