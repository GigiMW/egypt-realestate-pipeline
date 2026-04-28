select
    title,
    price_raw,
    location,
    area_sqm,
    bedrooms,
    bathrooms,
    url,
    cast(scraped_at as timestamp) as scraped_at,
    page,
    try_cast(replace(regexp_extract(price_raw, '([0-9][0-9,]*)', 1), ',', '') as double) as price_egp,
    try_cast(replace(regexp_extract(area_sqm, '([0-9][0-9,]*)', 1), ',', '') as double) as area_sqm_value,
    case
        when try_cast(replace(regexp_extract(price_raw, '([0-9][0-9,]*)', 1), ',', '') as double) is not null 
         and try_cast(replace(regexp_extract(area_sqm, '([0-9][0-9,]*)', 1), ',', '') as double) is not null 
         and try_cast(replace(regexp_extract(area_sqm, '([0-9][0-9,]*)', 1), ',', '') as double) > 0
            then round(
                try_cast(replace(regexp_extract(price_raw, '([0-9][0-9,]*)', 1), ',', '') as double) / 
                try_cast(replace(regexp_extract(area_sqm, '([0-9][0-9,]*)', 1), ',', '') as double), 
                2)
    end as price_per_sqm_egp
from main.raw_listings
where title is not null
  and url is not null