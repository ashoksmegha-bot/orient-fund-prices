"""Reads the latest fund prices (NAV) from public pages and writes prices.json.

Sources, by ISIN: FT Markets fund page (markets.ft.com), and the BlackRock
product page when a link is given in funds.csv. The newest date wins; on the
same date BlackRock (the fund house) wins. If every source fails for a fund,
the last good price is kept. Standard library only.
"""
import csv, json, re, time, html, datetime, urllib.request, urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
MON = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


def get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-GB,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def num(s):
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def ft(isin, cur):
    url = f"https://markets.ft.com/data/funds/tearsheet/summary?s={isin}:{cur}"
    page = get(url)
    if isin not in page:
        raise ValueError("FT page is not for this ISIN")
    m = re.search(r'class="mod-ui-data-list__value">([^<]+)<', page)
    d = re.search(r"as of ([A-Z][a-z]{2}) (\d{1,2}) (\d{4})", page)
    c = re.search(r"Price \(([A-Z]{3})\)", page)
    if not (m and d):
        raise ValueError("no price on FT page")
    nav = num(m.group(1))
    date = f"{d.group(3)}-{MON[d.group(1).lower()]:02d}-{int(d.group(2)):02d}"
    return {"nav": nav, "date": date, "cur": c.group(1) if c else cur,
            "src": "FT Markets", "url": url}


def blackrock(url, isin):
    page = get(url)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    k = re.search(r"ISIN ([A-Z]{2}[A-Z0-9]{9}\d)", text)
    if k and k.group(1) != isin:
        raise ValueError(f"BlackRock page is for {k.group(1)}, not {isin}")
    m = re.search(r"NAV as of (\d{1,2})-([A-Za-z]{3})-(\d{4}) ([A-Z]{3}) ([\d,]+\.\d+)", text)
    if not m:
        raise ValueError("no NAV on BlackRock page")
    date = f"{m.group(3)}-{MON[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return {"nav": num(m.group(5)), "date": date, "cur": m.group(4),
            "src": "BlackRock", "url": url}


def main():
    try:
        old = json.load(open("prices.json")).get("funds", {})
    except Exception:
        old = {}
    out, log = {}, []
    for row in csv.DictReader(open("funds.csv", newline="", encoding="utf-8")):
        code, isin, cur = row["code"], row["isin"].strip(), row["currency"] or "USD"
        got = []
        use = (row.get("sources") or "ft+blackrock").split("+")
        for name, fn in (("FT", lambda: ft(isin, cur)),
                         ("BlackRock", lambda: blackrock(row["blackrock_url"], isin))):
            if name == "FT" and "ft" not in use:
                continue
            if name == "BlackRock" and ("blackrock" not in use or not row.get("blackrock_url")):
                continue
            try:
                v = fn()
                if v["nav"] and v["nav"] > 0 and v["cur"] == cur:
                    got.append(v)
                else:
                    log.append(f"{code} {name}: currency {v['cur']} or price {v['nav']} rejected")
            except Exception as e:
                log.append(f"{code} {name}: {type(e).__name__} {str(e)[:80]}")
            time.sleep(0.4)
        if got:
            best = max(got, key=lambda v: (v["date"], v["src"] == "BlackRock"))
            best["isin"] = isin
            out[code] = best
        elif code in old:
            out[code] = dict(old[code], stale=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    json.dump({"checked_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "count": len(out), "funds": out, "errors": log},
              open("prices.json", "w"), indent=1, sort_keys=True)
    print(f"{len(out)} prices, {len(log)} source errors")
    for line in log:
        print(" ", line)


if __name__ == "__main__":
    main()
