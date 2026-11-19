-- Map each listing to a clean area name.
--
-- The scraped `location` is free text and often junk ("the", "very", ...),
-- so we search both the title and the location for known keywords from the
-- `location_areas` seed. When several keywords match, the longest one wins:
-- "mountain view icity october" beats "mountain view", "suez road" beats "suez".

with listings as (
    select * from {{ ref('stg_listings') }}
),

keywords as (
    select lower(trim(keyword)) as keyword, area
    from {{ ref('location_areas') }}
),

matches as (
    select
        l.url,
        k.area,
        row_number() over (
            partition by l.url
            order by length(k.keyword) desc, k.area
        ) as match_rank
    from listings l
    join keywords k
        on regexp_matches(
            lower(coalesce(l.title, '') || ' | ' || coalesce(l.location, '')),
            '\b' || k.keyword || '\b'
        )
)

select
    l.*,
    coalesce(m.area, 'Unknown') as area
from listings l
left join matches m
    on l.url = m.url
   and m.match_rank = 1
