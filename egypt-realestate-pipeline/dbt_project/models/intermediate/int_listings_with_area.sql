-- Map each listing to a clean area name.
--
-- Both the title and `location` are searched for keywords from the
-- `location_areas` seed. Newer scrapes carry Dubizzle's structured address
-- ("compound, locality") in `location`; older ones only have free text, which
-- is often junk ("the", "very"). The longest matching keyword wins
-- ("mountain view icity october" beats "mountain view", "new giza" beats "giza");
-- on a tie, a match in `location` beats one in the title.

with listings as (
    select * from {{ ref('stg_listings') }}
),

keywords as (
    select lower(trim(keyword)) as keyword, area
    from {{ ref('location_areas') }}
),

texts as (
    select url, snapshot_date, 1 as source_rank, lower(coalesce(location, '')) as txt from listings
    union all
    select url, snapshot_date, 2 as source_rank, lower(coalesce(title, '')) as txt from listings
),

matches as (
    select
        t.url,
        t.snapshot_date,
        k.area,
        row_number() over (
            partition by t.url, t.snapshot_date
            order by length(k.keyword) desc, t.source_rank, k.area
        ) as match_rank
    from texts t
    join keywords k
        on regexp_matches(t.txt, '\b' || k.keyword || '\b')
)

select
    l.*,
    coalesce(m.area, 'Unknown') as area
from listings l
left join matches m
    on l.url = m.url
   and l.snapshot_date = m.snapshot_date
   and m.match_rank = 1
