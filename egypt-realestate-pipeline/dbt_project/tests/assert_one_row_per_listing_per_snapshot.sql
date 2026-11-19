-- A listing must appear at most once per snapshot; duplicates would double-count
-- it in every average.
select url, snapshot_date, count(*) as n
from {{ ref('int_listings_with_area') }}
group by url, snapshot_date
having count(*) > 1
