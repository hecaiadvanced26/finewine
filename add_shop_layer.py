"""
add_shop_layer.py - creates shop_inventory.json: FICTIONAL price, stock and bottle size per wine.
Everything in this file is synthetic (random, seeded). It exists only so the order demo has something to sell.
Slides must say: "stock, prices and order acceptance are simulated".
"""
import json, random, sys
SEED = 11
wines = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "wines.json", encoding="utf-8"))
rnd = random.Random(SEED)
BASE = {"Red Wine": 11, "White Wine": 9, "Rosé Wine": 8, "Sparkling": 14, "Dessert Wine": 18}
inv = {}
for w in wines:
    rating = w.get("community_avg_rating") or 3.6
    price = max(4.5, BASE.get(w["wine_type"], 10) * (1 + (rating - 3.6) * 0.6) * rnd.uniform(0.8, 1.3))
    stock = 0 if rnd.random() < 0.15 else (rnd.randint(1, 3) if rnd.random() < 0.15 else rnd.randint(4, 24))
    ml = 375 if w["wine_type"] == "Dessert Wine" and rnd.random() < 0.6 else (1500 if rnd.random() < 0.02 else 750)
    inv[w["id"]] = {"price_eur": round(price * 2) / 2, "stock": stock, "bottle_ml": ml}
json.dump({"meta": {"synthetic": True, "seed": SEED, "note": "Fictional demo data. Not real prices or stock."}, "inventory": inv},
          open("shop_inventory.json", "w", encoding="utf-8"), indent=1)
print(len(inv), "items; out of stock:", sum(v["stock"] == 0 for v in inv.values()))
