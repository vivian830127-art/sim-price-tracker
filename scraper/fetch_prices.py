# -*- coding: utf-8 -*-
"""
每日抓取 PChome 即時售價 → data/latest.json + data/history.csv
- 依 config/products.json(由 excel_to_config.py 產生)逐一查詢商品即時價格
- 與前一次紀錄比較:紅漲 / 藍降
- 抓不到的品項保留 Excel 售價,標記 live=null
"""
import json
import csv
import time
import datetime
import pathlib
import urllib.request
import re

sys_path_hack = pathlib.Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(sys_path_hack))
from excel_to_config import compute  # 重用與 Excel 驗算一致的公式

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "products.json"
LATEST = ROOT / "data" / "latest.json"
HISTORY = ROOT / "data" / "history.csv"

PROD_API = ("https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/button"
            "&id={pid}&fields=Id,Price,Qty")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://24h.pchome.com.tw/",
}
RETRY = 2
SLEEP = 1.5


def fetch_price(pid):
    """回傳該 PChome 商品目前售價,失敗回 None。"""
    url = PROD_API.format(pid=pid)
    for i in range(RETRY):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            for v in data.values():
                p = (v or {}).get("Price") or {}
                if p.get("P") is not None:
                    return int(p["P"])
                if p.get("M") is not None:
                    return int(p["M"])
        except Exception:  # noqa: BLE001
            time.sleep(2 * (i + 1))
    return None


def load_history():
    rows = []
    if HISTORY.exists():
        with HISTORY.open(encoding="utf-8") as f:
            rows = [r for r in csv.reader(f)][1:]
    return rows  # [date, key, live_price, quote]


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    products = cfg["products"]
    fees = cfg["fees"]

    # 套用 Fastmove 報價:以「加值方案」逐行比對(一格多行則取第一個對到的)
    norm = lambda s: re.sub(r"\s+", "", str(s or ""))
    fq_file = ROOT / "data" / "fastmove_quotes.json"
    fquotes = json.loads(fq_file.read_text(encoding="utf-8")) if fq_file.exists() else {}
    matched = 0
    for p in products:
        plan_lines = [norm(x) for x in str(p.get("加值方案") or "").split("\n") if norm(x)]
        newq = None
        for line in plan_lines:
            line = re.sub(r"\(\$?\d+\)$", "", line)  # 去掉尾端 ($21) 之類註記
            if line in fquotes:
                newq = fquotes[line]
                break
        p["報價來源"] = "Fastmove" if newq is not None else "Excel"
        if newq is not None and newq != p["浮動報價"]:
            p["浮動報價"] = newq
            p.update(compute(p["售價"], p["商品數量"], newq, p["天數"], p["平台"], fees))
        if newq is not None:
            matched += 1
    if fquotes:
        print(f"Fastmove 報價套用:{matched}/{len(products)} 列")
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

    rows = load_history()
    # 每個 key 最近一筆(非今天)的紀錄,用來判斷漲跌
    prev = {}
    for d, k, lp, q in rows:
        if d != today:
            prev[k] = {"live": float(lp) if lp else None,
                       "quote": float(q) if q else None}

    out = []
    for p in products:
        live = fetch_price(p["pchome_id"]) if p.get("pchome_id") else None
        if p.get("pchome_id"):
            time.sleep(SLEEP)
        pv = prev.get(p["key"], {})

        def trend(cur, old):
            if cur is None or old is None:
                return 0
            return 1 if cur > old else (-1 if cur < old else 0)

        out.append({
            **p,
            "即時售價": live,
            "售價趨勢": trend(live, pv.get("live")),
            "報價趨勢": trend(p["浮動報價"], pv.get("quote")),
            "前次即時售價": pv.get("live"),
            "前次浮動報價": pv.get("quote"),
        })

    LATEST.parent.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps({
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
        "products": out,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = [r for r in rows if r[0] != today]
    for p in out:
        rows.append([today, p["key"],
                     "" if p["即時售價"] is None else str(p["即時售價"]),
                     str(p["浮動報價"])])
    with HISTORY.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "key", "live_price", "quote"])
        w.writerows(rows)

    ok = sum(1 for p in out if p["即時售價"] is not None)
    print(f"完成:{ok}/{len(out)} 個品項取得即時售價")


if __name__ == "__main__":
    main()
