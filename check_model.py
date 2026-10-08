"""
check_model.py - checks whether OpenRouter models fit this project BEFORE you build on them.
  1) static (no key needed): is the model listed? does it list 'tools' / 'tool_choice' / 'response_format' in supported_parameters? price, context size
  2) live (needs OPENROUTER_API_KEY + `pip install openai`): plain call, tool-call round trip, enum obedience (French 'cerise' -> 'cherry'),
     JSON mode, and the embedding model (cross-language sanity check).  A few cents at most.
Usage: python check_model.py MODEL_ID [MODEL_ID ...] [--emb EMB_MODEL_ID] [--static-only]
Writes model_check.json - paste it back / put the numbers on your cost slide (note the date and currency).
"""
import os, sys, json, time, math, urllib.request

def get_models(query=""):
    req = urllib.request.Request("https://openrouter.ai/api/v1/models" + query, headers={"User-Agent": "capstone-model-check"})
    return json.load(urllib.request.urlopen(req, timeout=30))["data"]

def static_info(m):
    sp = m.get("supported_parameters") or []; pr = m.get("pricing") or {}
    def per_m(x):
        try: return round(float(x) * 1e6, 4)          # ASSUMES the listed price is per token - verify on the model page
        except Exception: return None
    return {"listed": True, "tools": "tools" in sp, "tool_choice": "tool_choice" in sp, "response_format": "response_format" in sp, "structured_outputs": "structured_outputs" in sp,
            "context_length": m.get("context_length"), "price_in_raw": pr.get("prompt"), "price_out_raw": pr.get("completion"),
            "price_in_per_M_if_per_token": per_m(pr.get("prompt")), "price_out_per_M_if_per_token": per_m(pr.get("completion"))}

def attempt(fn):
    try: return fn()
    except Exception as e: return {"error": str(e)[:200]}

TOOLS = [{"type": "function", "function": {"name": "search_wines", "description": "Search wines by aroma tag.",
          "parameters": {"type": "object", "properties": {"flavours": {"type": "array", "items": {"type": "string", "enum": ["cherry", "lemon", "pear"]}}}, "required": ["flavours"]}}}]

def live_chat(client, mid):
    out = {}
    def plain():
        t = time.time(); r = client.chat.completions.create(model=mid, messages=[{"role": "user", "content": "Reply with the single word: ok"}], temperature=0, max_tokens=20)
        return {"ok": "ok" in (r.choices[0].message.content or "").lower(), "latency_s": round(time.time() - t, 2), "usage_returned": getattr(r, "usage", None) is not None}
    out["plain"] = attempt(plain)
    def tools():
        msgs = [{"role": "user", "content": "Je cherche un vin avec des notes de cerise."}]
        r = client.chat.completions.create(model=mid, messages=msgs, tools=TOOLS, tool_choice="auto", temperature=0)
        m = r.choices[0].message; tcs = m.tool_calls or []
        if not tcs: return {"tool_call_returned": False, "text": (m.content or "")[:100]}
        args = json.loads(tcs[0].function.arguments)
        msgs += [{"role": "assistant", "content": m.content or "", "tool_calls": [{"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in tcs]}]
        msgs += [{"role": "tool", "tool_call_id": t.id, "content": json.dumps({"matches_total": 1, "wines": [{"name": "Test Wine", "price_eur": 9.5}]})} for t in tcs]
        r2 = client.chat.completions.create(model=mid, messages=msgs, tools=TOOLS, temperature=0)
        return {"tool_call_returned": True, "valid_json_args": True, "enum_mapped_cerise_to_cherry": args.get("flavours") == ["cherry"],
                "roundtrip_answer_uses_tool_result": "9.5" in (r2.choices[0].message.content or "") or "9,5" in (r2.choices[0].message.content or "")}
    out["tools"] = attempt(tools)
    def jmode():
        r = client.chat.completions.create(model=mid, messages=[{"role": "user", "content": 'Return the JSON object {"ok": true} and nothing else.'}], temperature=0, response_format={"type": "json_object"})
        return {"parses": json.loads(r.choices[0].message.content).get("ok") is True}
    out["json_mode"] = attempt(jmode)
    return out

def live_emb(client, emb):
    def f():
        v = [d.embedding for d in client.embeddings.create(model=emb, input=["cherry", "cerise", "tractor engine oil"]).data]
        cos = lambda a, b: sum(x * y for x, y in zip(a, b)) / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))
        return {"dims": len(v[0]), "cos_cherry_cerise": round(cos(v[0], v[1]), 3), "cos_cherry_tractor": round(cos(v[0], v[2]), 3), "cross_language_ok": cos(v[0], v[1]) > cos(v[0], v[2])}
    return attempt(f)

def main(argv):
    emb = argv[argv.index("--emb") + 1] if "--emb" in argv else None
    ids = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--emb")]
    res = {"date": time.strftime("%Y-%m-%d"), "models": {}, "embedding": {}}
    raw = attempt(lambda: get_models())
    if isinstance(raw, dict): res["static_error"] = raw["error"]; print("Could not fetch the model list:", raw["error"]); raw = []
    listed = {m["id"]: m for m in raw}
    raw_e = attempt(lambda: get_models("?output_modalities=embeddings")); emb_listed = {m["id"]: m for m in raw_e} if isinstance(raw_e, list) else {}
    for i in ids: res["models"][i] = static_info(listed[i]) if i in listed else {"listed": False}
    if emb: res["embedding"] = {"model": emb, "listed_as_embedding_model": emb in emb_listed, "price_raw": (emb_listed.get(emb) or {}).get("pricing")}
    if "--static-only" not in argv:
        key = os.environ.get("OPENROUTER_API_KEY") or sys.exit("Set OPENROUTER_API_KEY (or use --static-only).")
        from openai import OpenAI; client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
        for i in ids: res["models"][i]["live"] = live_chat(client, i)
        if emb: res["embedding"]["live"] = live_emb(client, emb)
    json.dump(res, open("model_check.json", "w"), indent=1); print(json.dumps(res, indent=1))

if __name__ == "__main__": main(sys.argv[1:])
