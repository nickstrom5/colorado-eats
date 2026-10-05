"""Overture extracts for official-record matching -> data/co

- calib_areas.json        Denver (city and county) and Boulder County outlines (unsimplified), for calibrate.py and colorado.py
- addresses_co.parquet    Overture address points statewide, to place license records that have no coordinates (the state's liquor
                          list and half of Denver's licenses) and researched addresses the map listings lack
"""
import os, json, time
import duckdb
from shapely import wkb
from shapely.geometry import mapping

RELEASE = "2026-09-23.1"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "co")
t = time.time()
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial; SET s3_region='us-west-2';")
areas = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=divisions/type=division_area/*.parquet"
rows = con.execute(f"""SELECT class, subtype, names.primary, ST_AsWKB(geometry) FROM read_parquet('{areas}', hive_partitioning=1)
  WHERE country = 'US' AND region = 'US-CO' AND ((subtype = 'locality' AND names.primary IN ('Denver', 'Boulder'))
        OR (subtype = 'county' AND names.primary IN ('Denver County', 'Boulder County')))""").fetchall()
json.dump({f"{name}|{sub}": mapping(wkb.loads(bytes(g))) for cls, sub, name, g in rows if cls == "land"}, open(f"{OUT}/calib_areas.json", "w"))
print("areas:", [f"{n}|{s}" for c, s, n, g in rows if c == "land"], round(time.time() - t), "s", flush=True)
addr = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=addresses/type=address/*.parquet"
con.execute(f"""COPY (SELECT number, street, unit, postcode, postal_city, address_levels[1].value AS state, address_levels[-1].value AS muni,
  ST_Y(geometry) lat, ST_X(geometry) lon FROM read_parquet('{addr}', hive_partitioning=1)
  WHERE country = 'US' AND bbox.xmin BETWEEN -109.1 AND -102.0 AND bbox.ymin BETWEEN 36.95 AND 41.05)
  TO '{OUT}/addresses_co.parquet' (FORMAT PARQUET)""")
print(con.execute(f"select count(*), count(*) filter (where state='CO') from '{OUT}/addresses_co.parquet'").fetchall(), round(time.time() - t), "s")
