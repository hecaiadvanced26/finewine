"""build_db.py - builds wine_shop.sqlite from wines.json + shop_inventory.json (inventory table is SYNTHETIC)."""
import json, sqlite3, sys, os
wines = json.load(open("wines.json", encoding="utf-8")); inv = json.load(open("shop_inventory.json", encoding="utf-8"))["inventory"]
if os.path.exists("wine_shop.sqlite"): os.remove("wine_shop.sqlite")
c = sqlite3.connect("wine_shop.sqlite")
c.executescript("""
CREATE TABLE wines(id TEXT PRIMARY KEY, winery TEXT, wine_name TEXT, vintage INTEGER, country TEXT, region TEXT, regional_style TEXT,
                   wine_type TEXT, user_rating REAL, community_avg_rating REAL, user_review TEXT);
CREATE TABLE flavours(wine_id TEXT, tag TEXT, provenance TEXT CHECK(provenance IN ('stated','guess')));
CREATE TABLE inventory(wine_id TEXT PRIMARY KEY, price_eur REAL, stock INTEGER CHECK(stock>=0), bottle_ml INTEGER, synthetic INTEGER DEFAULT 1);
CREATE TABLE orders(order_id TEXT PRIMARY KEY, idempotency_key TEXT UNIQUE, status TEXT, lines_json TEXT, total_eur REAL, created_at TEXT);
CREATE INDEX ix_fl ON flavours(tag, wine_id);""")
for w in wines:
    c.execute("INSERT INTO wines VALUES (?,?,?,?,?,?,?,?,?,?,?)", (w["id"], w["winery"], w["wine_name"], w["vintage"], w["country"], w["region"],
              w["regional_style"], w["wine_type"], w["user_rating"], w["community_avg_rating"], w["user_review"]))
    for t in w["flavours_stated"]: c.execute("INSERT INTO flavours VALUES (?,?,'stated')", (w["id"], t))
    for t in w["flavours_inferred"]: c.execute("INSERT INTO flavours VALUES (?,?,'guess')", (w["id"], t))
    i = inv[w["id"]]; c.execute("INSERT INTO inventory VALUES (?,?,?,?,1)", (w["id"], i["price_eur"], i["stock"], i["bottle_ml"]))
c.commit(); print({t: c.execute(f"select count(*) from {t}").fetchone()[0] for t in ("wines", "flavours", "inventory", "orders")})
