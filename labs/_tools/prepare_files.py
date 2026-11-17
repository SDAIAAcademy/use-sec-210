# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Writes the synthetic file pack of USE-SEC-210 into labs/files/ and the trainer's key into
labs/solutions/key.json.

    uv run labs/_tools/prepare_files.py

Everything is invented: Sahab Group, its people, its vendors, its customers, its sites and its
numbers. One seed (210), Python's standard library only, the same bytes on every run.

What is a "model" here:
- Istishraf, the demand forecast, is fitted for real in this script: a least-squares regression
  per product on the first year's calendar and promotion features, scored on the second year.
- Mukhtarat's lists, Saerak's discounts, Baqaa's deciles, Rasd's scores and Subat's effect are
  synthetic outputs drawn with planted properties (listed in labs/solutions/answer_key.md).
No language model is called, here or in any lab.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_texts as T  # noqa: E402

LABS = Path(__file__).resolve().parent.parent
FILES = LABS / "files"
SOL = LABS / "solutions"
SEED = 210

KEY: dict = {}


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def r2(x: float) -> float:
    return round(x + 0.0, 2)


def r4(x: float) -> float:
    return round(x + 0.0, 4)


# ---------------------------------------------------------------------------------------------
# Retail: weekly sales of 50 products over two years (labs 1.2, 1.3, 1.4)
# ---------------------------------------------------------------------------------------------

START = dt.date(2024, 12, 30)  # Monday of week 1
RAMADAN = [(dt.date(2025, 3, 1), dt.date(2025, 3, 29)), (dt.date(2026, 2, 18), dt.date(2026, 3, 19))]
EID_FITR = [dt.date(2025, 3, 30), dt.date(2026, 3, 20)]
EID_ADHA = [dt.date(2025, 6, 6), dt.date(2026, 5, 27)]
WHITE_FRIDAY = [dt.date(2025, 11, 28), dt.date(2026, 11, 27)]
SCHOOL = [dt.date(2025, 8, 24), dt.date(2026, 8, 23)]

GROUPS = ["fresh", "dairy", "staples", "beverages", "household"]
# base range, Ramadan lift, pre-Ramadan lift, Eid lift, summer lift, white Friday lift, school lift,
# promotions per year, promotion lift, noise
GROUP_SPEC = {
    "fresh":     dict(base=(3000, 9000), ram=0.25, pre=0.10, eid=-0.10, summer=-0.05, wf=0.00, school=0.00, promos=2, lift=0.30, noise=0.09),
    "dairy":     dict(base=(4000, 12000), ram=0.30, pre=0.08, eid=-0.08, summer=0.05, wf=0.00, school=0.05, promos=3, lift=0.30, noise=0.07),
    "staples":   dict(base=(2000, 8000), ram=0.20, pre=0.45, eid=-0.15, summer=0.00, wf=0.05, school=0.00, promos=2, lift=0.35, noise=0.06),
    "beverages": dict(base=(3000, 10000), ram=0.40, pre=0.15, eid=0.10, summer=0.30, wf=0.10, school=0.00, promos=6, lift=0.70, noise=0.10),
    "household": dict(base=(1000, 4000), ram=0.05, pre=0.05, eid=0.00, summer=0.00, wf=1.00, school=0.20, promos=6, lift=0.90, noise=0.10),
}


def week_flags(w: int) -> dict:
    s = START + dt.timedelta(days=7 * (w - 1))
    days = [s + dt.timedelta(days=i) for i in range(7)]
    ram = any(sum(1 for d in days if a <= d <= b) >= 3 for a, b in RAMADAN)
    pre = any(a - dt.timedelta(days=7) <= s < a - dt.timedelta(days=0) and not ram for a, _ in RAMADAN)
    eid = any(any(abs((d - e).days) <= 1 for d in days) for e in EID_FITR + EID_ADHA)
    wf = any(d in WHITE_FRIDAY for d in days)
    school = any(0 <= (s - x).days + 7 <= 13 for x in SCHOOL)
    summer = s.month in (6, 7, 8)
    return dict(start=s, ramadan=int(ram), pre=int(pre and not ram), eid=int(eid), wf=int(wf),
                school=int(school), summer=int(summer))


FEATURES = ["const", "promo", "ramadan", "pre", "eid", "wf", "school", "summer"]


def solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        piv = m[c][c]
        for k in range(c, n + 1):
            m[c][k] /= piv
        for r in range(n):
            if r != c and m[r][c] != 0:
                f = m[r][c]
                for k in range(c, n + 1):
                    m[r][k] -= f * m[c][k]
    return [m[i][n] for i in range(n)]


def fit_ls(x: list[list[float]], y: list[float], ridge: float = 1e-3) -> list[float]:
    k = len(x[0])
    xtx = [[sum(r[i] * r[j] for r in x) + (ridge * len(y) if i == j and i > 0 else 0) for j in range(k)] for i in range(k)]
    xty = [sum(r[i] * yy for r, yy in zip(x, y)) for i in range(k)]
    return solve(xtx, xty)


def retail(rng: random.Random) -> None:
    weeks = list(range(1, 105))
    flags = {w: week_flags(w) for w in weeks}
    rows = []
    products = []
    pid = 0
    for g in GROUPS:
        spec = GROUP_SPEC[g]
        for i in range(10):
            pid += 1
            name_ar = T.PRODUCTS[g][i]
            base = rng.uniform(*spec["base"])
            products.append((pid, g, name_ar))
            promo_weeks = set()
            for year in (0, 1):
                pool = [w for w in weeks[year * 52:(year + 1) * 52] if not flags[w]["eid"]]
                promo_weeks |= set(rng.sample(pool, spec["promos"]))
            for w in weeks:
                f = flags[w]
                promo = int(w in promo_weeks)
                mult = (1 + spec["ram"] * f["ramadan"] + spec["pre"] * f["pre"] + spec["eid"] * f["eid"]
                        + spec["summer"] * f["summer"] + spec["wf"] * f["wf"] + spec["school"] * f["school"]
                        + spec["lift"] * promo)
                demand = base * mult * (1 + rng.gauss(0, spec["noise"]))
                demand = max(50.0, demand)
                # stock-outs: likelier in promotion and Ramadan weeks, and in year 1
                p_out = 0.015 + 0.20 * promo + 0.05 * f["ramadan"] + (0.06 * f["pre"] if g == "staples" else 0)
                if w > 52:
                    p_out *= 0.4
                out = int(rng.random() < p_out)
                sales = demand * rng.uniform(0.55, 0.75) if out else demand
                rows.append(dict(pid=pid, group=g, name=name_ar, week=w, f=f, promo=promo, stockout=out,
                                 sales=int(round(sales))))
    # Istishraf: a least-squares fit per product on year 1 (stock-out weeks left out), scored on year 2
    by_p: dict[int, list[dict]] = {}
    for r in rows:
        by_p.setdefault(r["pid"], []).append(r)
    for pid_, rs in by_p.items():
        def feats(r):
            f = r["f"]
            return [1.0, r["promo"], f["ramadan"], f["pre"], f["eid"], f["wf"], f["school"], f["summer"]]
        train = [r for r in rs if r["week"] <= 52 and not r["stockout"]]
        beta = fit_ls([feats(r) for r in train], [r["sales"] for r in train])
        for r in rs:
            r["model"] = int(round(sum(b * v for b, v in zip(beta, feats(r))))) if r["week"] > 52 else None
        for r in rs:
            if r["week"] > 52:
                last = rs[r["week"] - 53]
                r["snaive"] = last["sales"]
                r["stockout_last_year"] = last["stockout"]

    header = ["product_id", "product", "group", "week", "week_start", "year", "promo", "ramadan",
              "stockout", "sales", "istishraf_forecast"]
    out = []
    for r in rows:
        out.append([r["pid"], r["name"], r["group"], r["week"], r["f"]["start"].isoformat(),
                    1 if r["week"] <= 52 else 2, r["promo"], r["f"]["ramadan"], r["stockout"], r["sales"],
                    "" if r["model"] is None else r["model"]])
    write_csv(FILES / "retail" / "sales_weekly.csv", header, out)

    y2 = [r for r in rows if r["week"] > 52]
    header2 = ["product_id", "product", "group", "week", "promo", "ramadan", "stockout",
               "stockout_last_year", "sales", "istishraf_forecast", "seasonal_naive"]
    write_csv(FILES / "start" / "forecast_errors_y2.csv", header2,
              [[r["pid"], r["name"], r["group"], r["week"], r["promo"], r["f"]["ramadan"], r["stockout"],
                r["stockout_last_year"], r["sales"], r["model"], r["snaive"]] for r in y2])

    # key: lab 1.2 (all year-2 rows, as the page asks)
    def wape(rs, col):
        return 100 * sum(abs(r[col] - r["sales"]) for r in rs) / sum(r["sales"] for r in rs)

    def bias(rs, col):
        return 100 * sum(r[col] - r["sales"] for r in rs) / sum(r["sales"] for r in rs)

    KEY["1.2"] = dict(rows=len(y2), wape_model=r2(wape(y2, "model")), wape_snaive=r2(wape(y2, "snaive")),
                      bias_model=r2(bias(y2, "model")), bias_snaive=r2(bias(y2, "snaive")))
    # key: lab 1.3 (stock-out weeks left out), errors priced per group
    cost = T.COST_BY_GROUP
    fee = T.FEE_PER_GROUP
    g13 = {}
    for g in GROUPS:
        rs = [r for r in y2 if r["group"] == g and not r["stockout"]]
        def money(col):
            tot = 0.0
            for r in rs:
                e = r[col] - r["sales"]
                tot += e * cost[g]["over"] if e > 0 else -e * cost[g]["under"]
            return tot
        cm, cs = money("model"), money("snaive")
        g13[g] = dict(rows=len(rs), wape_model=r2(wape(rs, "model")), wape_snaive=r2(wape(rs, "snaive")),
                      cost_model=int(round(cm)), cost_snaive=int(round(cs)), saving=int(round(cs - cm)),
                      net=int(round(cs - cm - fee)), earns=bool(cs - cm > fee))
    KEY["1.3"] = dict(groups=g13, fee_per_group=fee)
    # key: lab 1.4, by week type, stock-out weeks left out
    clean = [r for r in y2 if not r["stockout"]]
    kinds = {
        "promo": [r for r in clean if r["promo"]],
        "ramadan": [r for r in clean if r["f"]["ramadan"] and not r["promo"]],
        "normal": [r for r in clean if not r["promo"] and not r["f"]["ramadan"]],
    }
    k14 = {k: dict(rows=len(v), wape_model=r2(wape(v, "model")), wape_snaive=r2(wape(v, "snaive")))
           for k, v in kinds.items()}
    ly = [r for r in clean if r["stockout_last_year"]]
    k14["after_stockout_last_year"] = dict(rows=len(ly), bias_snaive=r2(bias(ly, "snaive")),
                                           bias_model=r2(bias(ly, "model")))
    k14["stockout_weeks_y2"] = sum(r["stockout"] for r in y2)
    k14["stockout_weeks_y1"] = sum(r["stockout"] for r in rows if r["week"] <= 52)
    KEY["1.4"] = k14


# ---------------------------------------------------------------------------------------------
# Recommender: offline test sessions (lab 1.5) and an A/B test (lab 1.6)
# ---------------------------------------------------------------------------------------------

def recommender(rng: random.Random) -> None:
    n_items = 400
    weights = [1 / (i ** 0.6) for i in range(1, n_items + 1)]  # item id = popularity rank
    tot = sum(weights)
    cum = []
    c = 0.0
    for w in weights:
        c += w / tot
        cum.append(c)

    def draw_item():
        u = rng.random()
        lo, hi = 0, n_items - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid] < u:
                lo = mid + 1
            else:
                hi = mid
        return lo + 1

    rows = []
    popular = [1, 2, 3, 4, 5]
    for s in range(1, 2001):
        seg = "returning" if rng.random() < 0.7 else "new"
        nxt = draw_item()
        # Mukhtarat: for a returning customer it sees the history, so it often holds the next item;
        # for a new customer it falls back to popular items, like the baseline
        if seg == "returning" and rng.random() < 0.12:
            rec = [nxt]
        else:
            rec = []
        while len(rec) < 5:
            cand = draw_item() if rng.random() < 0.55 else rng.randint(1, 30)
            if cand not in rec:
                rec.append(cand)
        rng.shuffle(rec)
        rows.append([s, seg, nxt] + rec + popular)
    header = ["session_id", "customer", "next_item", "m1", "m2", "m3", "m4", "m5", "p1", "p2", "p3", "p4", "p5"]
    write_csv(FILES / "retail" / "reco_offline.csv", header, rows)

    def hit(r, cols):
        return int(r[2] in [r[i] for i in cols])
    mcols, pcols = range(3, 8), range(8, 13)
    res = {}
    for name, sub in [("all", rows), ("returning", [r for r in rows if r[1] == "returning"]),
                      ("new", [r for r in rows if r[1] == "new"])]:
        res[name] = dict(sessions=len(sub), hit_model=r2(100 * sum(hit(r, mcols) for r in sub) / len(sub)),
                         hit_popular=r2(100 * sum(hit(r, pcols) for r in sub) / len(sub)))
    recs = [r[i] for r in rows for i in mcols]
    res["share_top50"] = r2(100 * sum(1 for x in recs if x <= 50) / len(recs))
    res["distinct_items"] = len(set(recs))
    res["random_hit"] = r2(100 * 5 / n_items)
    KEY["1.5"] = res


def ab_test(rng: random.Random) -> None:
    rows = []
    base_conv = 0.060
    aov_a = 182.0
    for day in range(1, 29):
        dow = (day - 1) % 7
        traffic = 18000 * (1.25 if dow in (3, 4) else 1.0) * (1 + rng.gauss(0, 0.04))
        week = (day - 1) // 7 + 1
        lift = {1: 0.095, 2: 0.045, 3: 0.018, 4: 0.012}[week]
        for arm in ("A", "B"):
            visitors = int(round(traffic * (0.5 + rng.gauss(0, 0.004))))
            conv = base_conv * (1 + (lift if arm == "B" else 0)) * (1 + rng.gauss(0, 0.02))
            orders = int(round(visitors * conv))
            aov = aov_a * (0.965 if arm == "B" else 1.0) * (1 + rng.gauss(0, 0.015))
            revenue = int(round(orders * aov))
            ret = int(round(orders * (0.052 if arm == "B" else 0.041) * (1 + rng.gauss(0, 0.08))))
            rows.append([day, week, arm, visitors, orders, revenue, ret])
    write_csv(FILES / "retail" / "ab_test_daily.csv",
              ["day", "week", "arm", "visitors", "orders", "revenue_sar", "returned_orders"], rows)

    def agg(sub):
        v = sum(r[3] for r in sub)
        o = sum(r[4] for r in sub)
        rev = sum(r[5] for r in sub)
        ret = sum(r[6] for r in sub)
        return v, o, rev, ret
    out = {}
    for label, days in [("week1", range(1, 8)), ("weeks34", range(15, 29)), ("all", range(1, 29))]:
        a = agg([r for r in rows if r[2] == "A" and r[0] in days])
        b = agg([r for r in rows if r[2] == "B" and r[0] in days])
        ca, cb = a[1] / a[0], b[1] / b[0]
        se = math.sqrt(ca * (1 - ca) / a[0] + cb * (1 - cb) / b[0])
        out[label] = dict(visitors_a=a[0], visitors_b=b[0], conv_a=r4(100 * ca), conv_b=r4(100 * cb),
                          lift_pct=r2(100 * (cb / ca - 1)), diff_pts=r4(100 * (cb - ca)),
                          ci_low_pts=r4(100 * (cb - ca - 1.96 * se)), ci_high_pts=r4(100 * (cb - ca + 1.96 * se)),
                          rpv_a=r2(a[2] / a[0]), rpv_b=r2(b[2] / b[0]), rpv_lift_pct=r2(100 * ((b[2] / b[0]) / (a[2] / a[0]) - 1)),
                          return_rate_a=r2(100 * a[3] / a[1]), return_rate_b=r2(100 * b[3] / b[1]))
    va, vb = out["all"]["visitors_a"], out["all"]["visitors_b"]
    exp = (va + vb) / 2
    chi = (va - exp) ** 2 / exp + (vb - exp) ** 2 / exp
    out["srm_share_a"] = r2(100 * va / (va + vb))
    out["srm_chi2"] = r2(chi)
    out["srm_p"] = r4(math.erfc(math.sqrt(chi / 2)))
    KEY["1.6"] = out


# ---------------------------------------------------------------------------------------------
# Pricing: Saerak's personalised offers (labs 1.7 and 1.8)
# ---------------------------------------------------------------------------------------------

def pricing(rng: random.Random) -> None:
    custs = []
    offers = []
    for cid in range(1, 6001):
        age = rng.choices(["18-29", "30-44", "45-59", "60+"], [0.27, 0.36, 0.24, 0.13])[0]
        income = rng.choices(["low", "middle", "high"], [0.30, 0.45, 0.25])[0]
        dev_w = {"low": [0.30, 0.30, 0.40], "middle": [0.40, 0.40, 0.20], "high": [0.65, 0.30, 0.05]}[income]
        if age == "60+":
            dev_w = [dev_w[0] * 0.6, dev_w[1], dev_w[2] * 1.8]
        device = rng.choices(["ios", "android_new", "android_old"], dev_w)[0]
        inst = int(rng.random() < {"low": 0.38, "middle": 0.22, "high": 0.08}[income] * (1.3 if age == "60+" else 1))
        c_mkt = int(rng.random() < 0.72)
        c_pers = int(rng.random() < (0.55 if c_mkt else 0.10))
        c_loc = int(rng.random() < 0.31)
        health = int(rng.random() < 0.09 + (0.07 if age in ("45-59", "60+") else 0))
        # Saerak's discount components (percentage points), applied whatever the consent flags say
        d_hist = max(0.0, rng.gauss(3.0, 1.0))
        near_comp = rng.random() < {"low": 0.22, "middle": 0.45, "high": 0.60}[income]
        d_loc = 4.0 if near_comp else 0.0
        d_dev = {"ios": -1.5, "android_new": 0.0, "android_old": 1.0}[device]
        d_inst = -2.5 if inst else 0.0
        d_age = -1.5 if age == "60+" else 0.0  # "loyal, less likely to switch": a hidden rule found in 1.8
        disc = max(0.0, d_hist + d_loc + d_dev + d_inst + d_age)
        used_loc = int(near_comp)
        custs.append([cid, age, income, device, inst, c_mkt, c_pers, c_loc])
        offers.append(dict(cid=cid, age=age, income=income, device=device, inst=inst, health=health,
                           c_mkt=c_mkt, c_pers=c_pers, c_loc=c_loc, d_hist=r2(d_hist), d_loc=r2(d_loc),
                           d_dev=r2(d_dev), d_inst=r2(d_inst), d_age=r2(d_age), disc=r2(disc),
                           used_loc=used_loc, price_index=r2(100 - disc)))
    write_csv(FILES / "pricing" / "customers.csv",
              ["customer_id", "age_band", "district_income", "device", "instalments_user",
               "consent_marketing", "consent_personalisation", "consent_location"], custs)
    write_csv(FILES / "pricing" / "offers_month.csv",
              ["customer_id", "discount_pct", "price_index", "used_purchase_history", "used_location",
               "used_device", "used_instalments", "used_age", "health_segment_offer"],
              [[o["cid"], o["disc"], o["price_index"], 1, o["used_loc"], 1, 1, 1, o["health"]] for o in offers])
    write_csv(FILES / "start" / "offers_with_groups.csv",
              ["customer_id", "age_band", "district_income", "device", "instalments_user", "discount_pct",
               "price_index", "from_history", "from_location", "from_device", "from_instalments", "from_age"],
              [[o["cid"], o["age"], o["income"], o["device"], o["inst"], o["disc"], o["price_index"], o["d_hist"],
                o["d_loc"], o["d_dev"], o["d_inst"], o["d_age"]] for o in offers])
    # key 1.7: offers that used an input without the consent it needs
    k = dict(customers=len(offers))
    k["history_without_personalisation"] = sum(1 for o in offers if not o["c_pers"])
    k["location_without_location_consent"] = sum(1 for o in offers if o["used_loc"] and not o["c_loc"])
    k["offers_without_marketing_consent"] = sum(1 for o in offers if not o["c_mkt"])
    k["health_segment_offers"] = sum(o["health"] for o in offers)
    k["fully_covered"] = sum(1 for o in offers if o["c_mkt"] and o["c_pers"] and (o["c_loc"] or not o["used_loc"]) and not o["health"])
    KEY["1.7"] = k
    # key 1.8: average discount and its components by group
    def avg(sub, f):
        return r2(sum(o[f] for o in sub) / len(sub))
    groups = {}
    for col, vals in [("age", ["18-29", "30-44", "45-59", "60+"]), ("income", ["low", "middle", "high"]),
                      ("device", ["ios", "android_new", "android_old"]), ("inst", [0, 1])]:
        groups[col] = {}
        for v in vals:
            sub = [o for o in offers if o[col] == v]
            groups[col][str(v)] = dict(n=len(sub), discount=avg(sub, "disc"), from_location=avg(sub, "d_loc"),
                                       from_instalments=avg(sub, "d_inst"), from_age=avg(sub, "d_age"),
                                       from_device=avg(sub, "d_dev"), price_index=avg(sub, "price_index"))
    groups["all"] = dict(n=len(offers), discount=avg(offers, "disc"))
    KEY["1.8"] = groups


# ---------------------------------------------------------------------------------------------
# Telecom: the retention trial (labs 2.1 to 2.3) and the campaign months (lab 2.4)
# ---------------------------------------------------------------------------------------------

P0 = {1: 0.025, 2: 0.050, 3: 0.090, 4: 0.170, 5: 0.370}
# effect of the offer on the 90-day churn probability (negative = fewer leave), by Baqaa risk band
EFFECT = {
    "out": {1: 0.015, 2: -0.010, 3: -0.070, 4: -0.080, 5: -0.015},
    "in":  {1: 0.015, 2: 0.000, 3: -0.030, 4: -0.035, 5: -0.005},
}
OFFER_COST = 50   # SAR per offer made: a one-month bill credit of 50 SAR
BASE = 400000     # postpaid customers the policies are applied to
TRIAL = 100000


def retention(rng: random.Random) -> None:
    rows = []
    for cid in range(1, TRIAL + 1):
        band = rng.randint(1, 5)
        contract = "out" if rng.random() < (0.25 + 0.10 * band) else "in"
        tenure = max(1, int(rng.gauss(32 - 3.5 * band, 12)))
        rev = int(round(max(60, rng.gauss(165, 55))))
        treated = int(rng.random() < 0.5)
        p = P0[band] * (1.3 if contract == "out" else 0.7) + (EFFECT[contract][band] if treated else 0)
        churn = int(rng.random() < min(max(p, 0.001), 0.95))
        rows.append([cid, band, "out_of_contract" if contract == "out" else "in_contract", tenure, rev, treated, churn])
    write_csv(FILES / "telecom" / "retention_trial.csv",
              ["customer_id", "baqaa_band", "contract", "tenure_months", "monthly_revenue_sar", "offered", "churned_90d"], rows)

    def rate(sub):
        return sum(r[6] for r in sub) / len(sub) if sub else float("nan")
    t = [r for r in rows if r[5]]
    c = [r for r in rows if not r[5]]
    k21 = dict(n=len(rows), n_offered=len(t), n_control=len(c),
               tenure_offered=r2(sum(r[3] for r in t) / len(t)), tenure_control=r2(sum(r[3] for r in c) / len(c)),
               revenue_offered=r2(sum(r[4] for r in t) / len(t)), revenue_control=r2(sum(r[4] for r in c) / len(c)),
               out_share_offered=r2(100 * sum(1 for r in t if r[2] == "out_of_contract") / len(t)),
               out_share_control=r2(100 * sum(1 for r in c if r[2] == "out_of_contract") / len(c)),
               churn_offered=r2(100 * rate(t)), churn_control=r2(100 * rate(c)))
    k21["uplift_all_pts"] = r2(100 * (rate(c) - rate(t)))
    top = lambda rs: [r for r in rs if r[1] == 5]
    k21["uplift_top_band_pts"] = r2(100 * (rate(top(c)) - rate(top(t))))
    k21["churn_control_top_band"] = r2(100 * rate(top(c)))
    k21["churn_offered_top_band"] = r2(100 * rate(top(t)))
    k21["by_band"] = {str(b): dict(churn_control=r2(100 * rate([r for r in c if r[1] == b])),
                                   churn_offered=r2(100 * rate([r for r in t if r[1] == b])),
                                   uplift_pts=r2(100 * (rate([r for r in c if r[1] == b]) - rate([r for r in t if r[1] == b]))))
                      for b in range(1, 6)}
    KEY["2.1"] = k21

    cells = []
    for contract in ("out_of_contract", "in_contract"):
        for band in range(5, 0, -1):
            sub = [r for r in rows if r[1] == band and r[2] == contract]
            ct = [r for r in sub if r[5]]
            cc = [r for r in sub if not r[5]]
            up = 100 * (rate(cc) - rate(ct))
            cells.append(dict(contract=contract, band=band, n=len(sub), n_offered=len(ct), n_control=len(cc),
                              churn_offered=r2(100 * rate(ct)), churn_control=r2(100 * rate(cc)), uplift_pts=r2(up),
                              revenue=r2(sum(r[4] for r in sub) / len(sub)), share=len(sub) / len(rows)))
    KEY["2.2"] = dict(cells=[{k: v for k, v in x.items() if k != "share"} for x in cells],
                      negative=[f"{x['contract']}:{x['band']}" for x in cells if x["uplift_pts"] < 0],
                      target=[f"{x['contract']}:{x['band']}" for x in cells if x["uplift_pts"] >= 3])

    # the start file of 2.3: the ten cells scaled to the base of 400,000, with the measured uplift
    start = []
    for x in cells:
        base_n = int(round(BASE * x["share"]))
        start.append([x["contract"], x["band"], base_n, x["uplift_pts"], x["revenue"], x["churn_control"]])
    write_csv(FILES / "start" / "uplift_cells.csv",
              ["contract", "baqaa_band", "customers_in_base", "uplift_pts", "avg_monthly_revenue_sar", "churn_without_offer_pct"],
              start)

    def policy(sel):
        offers = retained = revenue = 0.0
        for s in start:
            if sel(s):
                offers += s[2]
                kept = s[2] * s[3] / 100
                retained += kept
                revenue += kept * s[4] * 12
        cost = offers * OFFER_COST
        return dict(offers=int(round(offers)), retained=int(round(retained)), revenue_12m=int(round(revenue)),
                    cost=int(round(cost)), net=int(round(revenue - cost)),
                    wasted=int(round(offers - retained)), wasted_pct=r2(100 * (offers - retained) / offers) if offers else 0)
    KEY["2.3"] = dict(offer_cost=OFFER_COST, base=BASE,
                      all=policy(lambda s: True),
                      top_band=policy(lambda s: s[1] == 5),
                      uplift3=policy(lambda s: s[3] >= 3))


def campaign(rng: random.Random) -> None:
    rows = []
    # months 1-4 with a 5% holdout, 5-7 without, month 8 with the holdout back (after retraining in month 6)
    true_uplift = {1: 3.1, 2: 2.9, 3: 3.0, 4: 2.8, 5: 2.7, 6: 1.2, 7: 0.9, 8: 0.8}
    churn_wo = {1: 11.8, 2: 12.1, 3: 11.6, 4: 12.0, 5: 11.9, 6: 7.4, 7: 6.9, 8: 6.8}
    for m in range(1, 9):
        targeted = int(rng.gauss(24000, 600))
        hold = int(round(targeted * 0.05)) if m in (1, 2, 3, 4, 8) else 0
        offered = targeted - hold
        stay_hold = 100 - churn_wo[m] + rng.gauss(0, 0.15)
        stay_off = stay_hold + true_uplift[m]
        model = "v1" if m < 6 else "v2"
        rows.append([m, model, targeted, offered, int(round(offered * stay_off / 100)), hold,
                     int(round(hold * stay_hold / 100)) if hold else ""])
    write_csv(FILES / "telecom" / "campaign_months.csv",
              ["month", "baqaa_version", "targeted", "offered", "offered_stayed", "holdout", "holdout_stayed"], rows)
    claim = []
    meas = []
    for r in rows:
        claim.append(r[4])
        if r[5]:
            up = r[4] / r[3] - r[6] / r[5]
            meas.append(dict(month=r[0], uplift_pts=r2(100 * up), incremental=int(round(up * r[3]))))
    KEY["2.4"] = dict(claimed_saved_total=sum(claim), measured=meas,
                      months_without_holdout=[r[0] for r in rows if not r[5]])


# ---------------------------------------------------------------------------------------------
# Network: a week of Rasd alerts against confirmed incidents (2.5, 2.6); energy pilot (2.7)
# ---------------------------------------------------------------------------------------------

REGIONS = ["central", "western", "eastern", "northern", "southern"]


def network(rng: random.Random) -> None:
    sites = [(s, rng.choice(REGIONS)) for s in range(1001, 2201)]
    incidents = []
    iid = 0
    for s, reg in rng.sample(sites, 72):
        iid += 1
        start = rng.randint(2, 160)
        dur = rng.choice([1, 2, 2, 3, 4, 6])
        sev = rng.choices(["critical", "major", "minor"], [0.2, 0.4, 0.4])[0]
        incidents.append([f"INC{iid:03d}", s, reg, start, min(167, start + dur), sev])
    planned = []
    for s, reg in rng.sample(sites, 40):
        h = rng.randint(0, 160)
        planned.append((s, h, h + 3))
    alerts = []
    aid = 0
    inc_by_site = {}
    for inc in incidents:
        inc_by_site.setdefault(inc[1], []).append(inc)
    region_of = dict(sites)
    # alerts tied to incidents: several per incident, scores high but not always
    for inc in incidents:
        strength = {"critical": 0.78, "major": 0.66, "minor": 0.55}[inc[5]] + rng.gauss(0, 0.12)
        n = rng.randint(1, 5)
        for _ in range(n):
            h = rng.randint(max(0, inc[3] - 1), inc[4])
            sc = min(0.99, max(0.30, strength + rng.gauss(0, 0.08)))
            alerts.append([None, inc[1], inc[2], h, r2(sc), rng.choice(["drop_rate", "throughput", "availability"]), 0])
    # alerts during planned works
    for s, a, b in planned:
        for _ in range(rng.randint(2, 4)):
            alerts.append([None, s, region_of[s], rng.randint(a, b), r2(min(0.99, max(0.3, rng.gauss(0.72, 0.1)))),
                           "availability", 1])
    # noise alerts
    for _ in range(2100):
        s, reg = rng.choice(sites)
        sc = 0.30 + rng.expovariate(1 / 0.10)
        if sc >= 1:
            continue
        alerts.append([None, s, reg, rng.randint(0, 167), r2(sc), rng.choice(["drop_rate", "throughput", "availability"]), 0])
    alerts.sort(key=lambda a: (a[3], a[1]))
    for a in alerts:
        aid += 1
        a[0] = f"A{aid:05d}"
    write_csv(FILES / "network" / "alerts_week.csv",
              ["alert_id", "site_id", "region", "hour_of_week", "score", "kpi", "planned_work"], alerts)
    write_csv(FILES / "network" / "incidents_week.csv",
              ["incident_id", "site_id", "region", "start_hour", "end_hour", "severity"], incidents)

    def match(a):
        for inc in inc_by_site.get(a[1], []):
            if inc[3] - 1 <= a[3] <= inc[4]:
                return inc[0]
        return ""
    matched = [(a, match(a)) for a in alerts]
    best = {}
    for a, m in matched:
        if m:
            best[m] = max(best.get(m, 0), a[4])
    write_csv(FILES / "start" / "alert_matches.csv",
              ["alert_id", "site_id", "hour_of_week", "score", "planned_work", "matched_incident"],
              [[a[0], a[1], a[3], a[4], a[6], m] for a, m in matched])
    write_csv(FILES / "start" / "incident_best_score.csv",
              ["incident_id", "severity", "best_alert_score"],
              [[i[0], i[5], best.get(i[0], 0)] for i in incidents])

    def at(t, skip_planned=False):
        sel = [(a, m) for a, m in matched if a[4] >= t and not (skip_planned and a[6])]
        tp = sum(1 for a, m in sel if m)
        found = [i for i in incidents if best.get(i[0], 0) >= t]
        crit = [i for i in incidents if i[5] == "critical"]
        return dict(alerts=len(sel), per_day=r2(len(sel) / 7), precision=r2(100 * tp / len(sel)) if sel else 0,
                    recall=r2(100 * len(found) / len(incidents)),
                    critical_recall=r2(100 * sum(1 for i in crit if best.get(i[0], 0) >= t) / len(crit)),
                    missed=len(incidents) - len(found))
    KEY["2.5"] = dict(alerts=len(alerts), incidents=len(incidents), vendor_threshold=0.4, at_vendor=at(0.4),
                      alerts_matched_at_vendor=sum(1 for a, m in matched if m and a[4] >= 0.4),
                      planned_alerts=sum(1 for a in alerts if a[6]),
                      critical=sum(1 for i in incidents if i[5] == "critical"))
    table = {}
    for t in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        table[f"{t:.1f}"] = at(t)
        table[f"{t:.1f}_no_planned"] = at(t, True)
    KEY["2.6"] = dict(capacity_per_day=T.NOC_CAPACITY_PER_DAY, table=table)


def energy(rng: random.Random) -> None:
    rows = []
    for i in range(80):
        group = "pilot" if i < 40 else "control"
        rural = int(rng.random() < 0.25)
        kwh_b = rng.uniform(260, 420) * (0.8 if rural else 1)
        season = 1 - 0.065 + rng.gauss(0, 0.015)
        effect = (1 - 0.085 + rng.gauss(0, 0.02)) if group == "pilot" else 1
        kwh_a = kwh_b * season * effect
        drop_b = rng.uniform(0.35, 0.65)
        d_drop = rng.gauss(0.0, 0.02) + (0.03 if group == "pilot" else 0) + (0.30 if group == "pilot" and rural and rng.random() < 0.4 else 0)
        rows.append([f"S{3001 + i}", group, "rural" if rural else "urban", r2(kwh_b), r2(kwh_a), r2(drop_b), r2(drop_b + d_drop)])
    write_csv(FILES / "network" / "energy_pilot.csv",
              ["site_id", "group", "area", "kwh_per_day_before", "kwh_per_day_after", "drop_rate_before_pct", "drop_rate_after_pct"], rows)

    def ch(sub, b, a):
        sb = sum(r[b] for r in sub)
        sa = sum(r[a] for r in sub)
        return 100 * (sa / sb - 1)
    p = [r for r in rows if r[1] == "pilot"]
    c = [r for r in rows if r[1] == "control"]
    md = lambda sub: sum(r[6] - r[5] for r in sub) / len(sub)
    KEY["2.7"] = dict(pilot_change_pct=r2(ch(p, 3, 4)), control_change_pct=r2(ch(c, 3, 4)),
                      did_pct=r2(ch(p, 3, 4) - ch(c, 3, 4)),
                      drop_change_pilot=r4(md(p)), drop_change_control=r4(md(c)),
                      did_drop=r4(md(p) - md(c)),
                      sites_over_guardrail=[r[0] for r in p if r[6] - r[5] > T.DROP_GUARDRAIL_PTS])


# ---------------------------------------------------------------------------------------------
# The map (2.8), pre-work and follow-up, the company profile and the use-case cards (1.1)
# ---------------------------------------------------------------------------------------------

def score_use_case(u: dict) -> dict:
    g = T.SCORING
    v = g["value_band"](u["measured_net_sar"])
    v = min(v, g["evidence_cap"][u["evidence"]])
    h = g["harm"][u["customer_harm"]]
    d = g["rights"][u["data_rights"]]
    total = 2 * v + h + d
    if d == 1 or v == 1:
        quad = "stop"
    elif v >= 4 and h >= 3:
        quad = "pursue"
    elif v >= 4:
        quad = "fix_first"
    else:
        quad = "test_cheaply"
    return dict(value=v, harm=h, rights=d, total=total, quadrant=quad)


def texts_and_map() -> None:
    for rel, text in T.TEXT_FILES.items():
        write_text(FILES / rel, text)
    write_csv(FILES / "retail" / "cost_by_group.csv", ["group", "cost_under_per_unit_sar", "cost_over_per_unit_sar"],
              [[g, T.COST_BY_GROUP[g]["under"], T.COST_BY_GROUP[g]["over"]] for g in GROUPS])
    write_csv(FILES / "use_cases.csv", ["case_id", "arm", "name", "description"], [list(x) for x in T.USE_CASES_1_1])
    write_csv(FILES / "chain_template.csv",
              ["case_id", "family", "data_in", "model_output", "decision_rule", "action", "decision_owner",
               "outcome_measure", "baseline_today"], [[x[0]] + [""] * 8 for x in T.USE_CASES_1_1])
    KEY["1.1"] = dict(cases=len(T.USE_CASES_1_1), key=T.CHAIN_KEY)
    hdr = ["uc_id", "arm", "use_case", "evidence", "measured_net_sar", "customer_harm", "data_rights", "notes"]
    write_csv(FILES / "map" / "use_cases.csv", hdr, [list(u.values()) for u in T.MAP_USE_CASES])
    write_csv(FILES / "map" / "map_template.csv",
              ["uc_id", "value_score", "harm_score", "rights_score", "total", "quadrant", "one_line_reason"],
              [[u["uc_id"]] + [""] * 6 for u in T.MAP_USE_CASES])
    scored = {u["uc_id"]: score_use_case(u) for u in T.MAP_USE_CASES}
    order = sorted(scored, key=lambda k: (-scored[k]["total"], k))
    KEY["2.8"] = dict(scores=scored, ranking=order)
    write_csv(FILES / "prework_sheet.csv", ["question", "your_answer"], [[q, ""] for q in T.PREWORK_QUESTIONS])
    write_csv(FILES / "followup_sheet.csv", ["field", "use_case_1", "use_case_2"], [[q, "", ""] for q in T.FOLLOWUP_FIELDS])


def main() -> None:
    rng = random.Random(SEED)
    retail(random.Random(SEED + 1))
    recommender(random.Random(SEED + 2))
    ab_test(random.Random(SEED + 3))
    pricing(random.Random(SEED + 4))
    retention(random.Random(SEED + 5))
    campaign(random.Random(SEED + 6))
    network(random.Random(SEED + 7))
    energy(random.Random(SEED + 8))
    texts_and_map()
    del rng
    SOL.mkdir(parents=True, exist_ok=True)
    (SOL / "key.json").write_text(json.dumps(KEY, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("files written:", sum(1 for p in FILES.rglob("*") if p.is_file()))


if __name__ == "__main__":
    main()
