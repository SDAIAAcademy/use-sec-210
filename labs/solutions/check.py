# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run the reference solution of every lab of USE-SEC-210 on the participants' files.

    uv run labs/solutions/check.py            # all labs
    uv run labs/solutions/check.py 1.3 2.2    # some labs

Every number is recomputed from labs/files/ (the files a participant opens), the way the lab page
tells a participant to compute it, and compared with key.json, which the file generator wrote.
Each lab starts from its own files: none reads the result of another lab.
Lab 1.1 checks the key against the use-case cards; 2.7 checks the location request's facts.
No lab of this course calls a language model. Nothing is written to disk.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABS = HERE.parent
FILES = LABS / "files"
KEY = json.loads((HERE / "key.json").read_text(encoding="utf-8"))
RUN: dict = {}


def lab(lab_id):
    def wrap(fn):
        RUN[lab_id] = fn
        return fn
    return wrap


def rows(rel: str) -> list[dict]:
    with (FILES / rel).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def text(rel: str) -> str:
    return (FILES / rel).read_text(encoding="utf-8")


def same(label, got, want, tol=0.0):
    ok = abs(float(got) - float(want)) <= tol if isinstance(want, (int, float)) and not isinstance(want, bool) else got == want
    if not ok:
        raise AssertionError(f"{label}: computed {got!r}, key {want!r}")


def show(*parts):
    print("   ", *parts)


def wape(rs, col):
    return 100 * sum(abs(float(r[col]) - float(r["sales"])) for r in rs) / sum(float(r["sales"]) for r in rs)


def bias(rs, col):
    return 100 * sum(float(r[col]) - float(r["sales"]) for r in rs) / sum(float(r["sales"]) for r in rs)


@lab("1.1")
def lab_1_1():
    cards = rows("use_cases.csv")
    k = KEY["1.1"]["key"]
    same("cards", len(cards), 10)
    same("key covers every card", sorted(k), sorted(c["case_id"] for c in cards))
    fam = {}
    for v in k.values():
        fam[v["family"]] = fam.get(v["family"], 0) + 1
    same("two cards per family", sorted(fam.values()), [2, 2, 2, 2, 2])
    desc = {c["case_id"]: c["description"] for c in cards}
    for cid, word in [("C02", "النقر"), ("C06", "دقة"), ("C08", "دقته"), ("C09", "تلقائيًّا")]:
        assert word in desc[cid], (cid, word)
        assert k[cid]["trap"], cid
    auto = sorted(c for c, v in k.items() if v["automatic"])
    show("families:", fam, "| automatic decisions:", auto)
    same("automatic", auto, ["C02", "C03", "C04", "C09"])


@lab("1.2")
def lab_1_2():
    rs = rows("retail/sales_weekly.csv")
    by_row = rs  # sorted by product, then week: the row 52 above is the same week last year
    y2 = []
    for i, r in enumerate(by_row):
        if r["year"] == "2":
            last = by_row[i - 52]
            assert last["product_id"] == r["product_id"] and int(last["week"]) == int(r["week"]) - 52
            y2.append(dict(r, snaive=last["sales"]))
    k = KEY["1.2"]
    same("rows", len(y2), k["rows"])
    for name, col in [("model", "istishraf_forecast"), ("snaive", "snaive")]:
        same(f"wape {name}", round(wape(y2, col), 2), k[f"wape_{name}"], 0.01)
        same(f"bias {name}", round(bias(y2, col), 2), k[f"bias_{name}"], 0.01)
    show(f"WAPE Istishraf {k['wape_model']}%, seasonal naive {k['wape_snaive']}%; bias {k['bias_model']}% and {k['bias_snaive']}%")


@lab("1.3")
def lab_1_3():
    rs = [r for r in rows("start/forecast_errors_y2.csv") if r["stockout"] == "0"]
    cost = {r["group"]: r for r in rows("retail/cost_by_group.csv")}
    fee = 220000
    assert "220,000" in text("retail/vendor_offer.txt")
    k = KEY["1.3"]["groups"]
    for g, kg in k.items():
        sub = [r for r in rs if r["group"] == g]
        def money(col):
            t = 0.0
            for r in sub:
                e = float(r[col]) - float(r["sales"])
                t += e * float(cost[g]["cost_over_per_unit_sar"]) if e > 0 else -e * float(cost[g]["cost_under_per_unit_sar"])
            return t
        cm, cs = money("istishraf_forecast"), money("seasonal_naive")
        same(f"{g} wape model", round(wape(sub, "istishraf_forecast"), 2), kg["wape_model"], 0.01)
        same(f"{g} wape snaive", round(wape(sub, "seasonal_naive"), 2), kg["wape_snaive"], 0.01)
        same(f"{g} saving", round(cs - cm), kg["saving"], 1)
        same(f"{g} earns", cs - cm > fee, kg["earns"])
        show(f"{g:10s} WAPE {kg['wape_model']:5.2f} vs {kg['wape_snaive']:5.2f}  saving {kg['saving']:>9,}  net {kg['net']:>9,}")
    same("staples does not earn", k["staples"]["earns"], False)


@lab("1.4")
def lab_1_4():
    rs = rows("start/forecast_errors_y2.csv")
    clean = [r for r in rs if r["stockout"] == "0"]
    kinds = {"promo": [r for r in clean if r["promo"] == "1"],
             "ramadan": [r for r in clean if r["ramadan"] == "1" and r["promo"] == "0"],
             "normal": [r for r in clean if r["ramadan"] == "0" and r["promo"] == "0"]}
    k = KEY["1.4"]
    for name, sub in kinds.items():
        same(f"{name} rows", len(sub), k[name]["rows"])
        same(f"{name} model", round(wape(sub, "istishraf_forecast"), 2), k[name]["wape_model"], 0.01)
        same(f"{name} snaive", round(wape(sub, "seasonal_naive"), 2), k[name]["wape_snaive"], 0.01)
        show(f"{name:8s} rows {len(sub):5d}  WAPE {k[name]['wape_model']:5.2f} vs {k[name]['wape_snaive']:5.2f}")
    ly = [r for r in clean if r["stockout_last_year"] == "1"]
    same("after stock-out bias snaive", round(bias(ly, "seasonal_naive"), 2), k["after_stockout_last_year"]["bias_snaive"], 0.01)
    same("after stock-out bias model", round(bias(ly, "istishraf_forecast"), 2), k["after_stockout_last_year"]["bias_model"], 0.01)
    same("stock-out weeks y2", sum(r["stockout"] == "1" for r in rs), k["stockout_weeks_y2"])
    show(f"weeks after a stock-out last year: {len(ly)}, seasonal naive bias {k['after_stockout_last_year']['bias_snaive']}%")


@lab("1.5")
def lab_1_5():
    rs = rows("retail/reco_offline.csv")
    k = KEY["1.5"]
    def hit(r, p):
        return r["next_item"] in [r[f"{p}{i}"] for i in range(1, 6)]
    for seg in ("all", "returning", "new"):
        sub = rs if seg == "all" else [r for r in rs if r["customer"] == seg]
        same(f"{seg} model", round(100 * sum(hit(r, "m") for r in sub) / len(sub), 2), k[seg]["hit_model"], 0.01)
        same(f"{seg} popular", round(100 * sum(hit(r, "p") for r in sub) / len(sub), 2), k[seg]["hit_popular"], 0.01)
        show(f"{seg:9s} hit@5 Mukhtarat {k[seg]['hit_model']}%  popular {k[seg]['hit_popular']}%")
    recs = [int(r[f"m{i}"]) for r in rs for i in range(1, 6)]
    same("share top 50", round(100 * sum(x <= 50 for x in recs) / len(recs), 2), k["share_top50"], 0.01)
    assert "11.9%" in text("retail/reco_vendor_note.txt")
    show(f"share of recommendations among the 50 best sellers: {k['share_top50']}%")


@lab("1.6")
def lab_1_6():
    rs = rows("retail/ab_test_daily.csv")
    k = KEY["1.6"]
    def agg(arm, days):
        sub = [r for r in rs if r["arm"] == arm and int(r["day"]) in days]
        return [sum(int(r[c]) for r in sub) for c in ("visitors", "orders", "revenue_sar", "returned_orders")]
    for label, days in [("week1", range(1, 8)), ("weeks34", range(15, 29)), ("all", range(1, 29))]:
        a, b = agg("A", days), agg("B", days)
        ca, cb = a[1] / a[0], b[1] / b[0]
        se = math.sqrt(ca * (1 - ca) / a[0] + cb * (1 - cb) / b[0])
        kk = k[label]
        same(f"{label} lift", round(100 * (cb / ca - 1), 2), kk["lift_pct"], 0.01)
        same(f"{label} ci low", round(100 * (cb - ca - 1.96 * se), 4), kk["ci_low_pts"], 0.0001)
        same(f"{label} ci high", round(100 * (cb - ca + 1.96 * se), 4), kk["ci_high_pts"], 0.0001)
        same(f"{label} rpv lift", round(100 * ((b[2] / b[0]) / (a[2] / a[0]) - 1), 2), kk["rpv_lift_pct"], 0.01)
        same(f"{label} returns b", round(100 * b[3] / b[1], 2), kk["return_rate_b"], 0.01)
        show(f"{label:7s} conv lift {kk['lift_pct']:5.2f}%  diff {kk['diff_pts']:.3f} pts  CI [{kk['ci_low_pts']:.3f}, {kk['ci_high_pts']:.3f}]  RPV {kk['rpv_lift_pct']}%  returns {kk['return_rate_a']}% vs {kk['return_rate_b']}%")
    va, vb = agg("A", range(1, 29))[0], agg("B", range(1, 29))[0]
    same("srm share", round(100 * va / (va + vb), 2), k["srm_share_a"], 0.01)
    show(f"sample ratio A {k['srm_share_a']}%, chi2 {k['srm_chi2']}, p {k['srm_p']}")


@lab("1.7")
def lab_1_7():
    cust = {r["customer_id"]: r for r in rows("pricing/customers.csv")}
    off = rows("pricing/offers_month.csv")
    k = KEY["1.7"]
    rule = text("pricing/saerak_rule.txt")
    assert "لا تقرأ القاعدة أعمدة الموافقة" in rule and "خالية من السكر" in rule
    j = [(o, cust[o["customer_id"]]) for o in off]
    same("history w/o personalisation", sum(1 for o, c in j if o["used_purchase_history"] == "1" and c["consent_personalisation"] == "0"), k["history_without_personalisation"])
    same("location w/o consent", sum(1 for o, c in j if o["used_location"] == "1" and c["consent_location"] == "0"), k["location_without_location_consent"])
    same("offers w/o marketing", sum(1 for o, c in j if c["consent_marketing"] == "0"), k["offers_without_marketing_consent"])
    same("health segment", sum(1 for o, c in j if o["health_segment_offer"] == "1"), k["health_segment_offers"])
    show(f"history without personalisation consent {k['history_without_personalisation']}, location without consent {k['location_without_location_consent']}, "
         f"no marketing consent {k['offers_without_marketing_consent']}, health segment {k['health_segment_offers']}, fully covered {k['fully_covered']} of {k['customers']}")


@lab("1.8")
def lab_1_8():
    rs = rows("start/offers_with_groups.csv")
    k = KEY["1.8"]
    cols = {"age": "age_band", "income": "district_income", "device": "device", "inst": "instalments_user"}
    for g, col in cols.items():
        for v, kv in k[g].items():
            sub = [r for r in rs if r[col] == v]
            same(f"{g}={v} discount", round(sum(float(r["discount_pct"]) for r in sub) / len(sub), 2), kv["discount"], 0.011)
            for comp in ("location", "instalments", "age"):
                same(f"{g}={v} {comp}", round(sum(float(r[f"from_{comp}"]) for r in sub) / len(sub), 2), kv[f"from_{comp}"], 0.011)
            show(f"{g:6s} {v:12s} n {kv['n']:5d}  discount {kv['discount']:5.2f}  location {kv['from_location']:5.2f}  instalments {kv['from_instalments']:5.2f}  age {kv['from_age']:5.2f}")


def trial():
    return rows("telecom/retention_trial.csv")


def rate(sub):
    return sum(r["churned_90d"] == "1" for r in sub) / len(sub)


@lab("2.1")
def lab_2_1():
    rs = trial()
    t = [r for r in rs if r["offered"] == "1"]
    c = [r for r in rs if r["offered"] == "0"]
    k = KEY["2.1"]
    same("tenure offered", round(sum(int(r["tenure_months"]) for r in t) / len(t), 2), k["tenure_offered"], 0.01)
    same("out share control", round(100 * sum(r["contract"] == "out_of_contract" for r in c) / len(c), 2), k["out_share_control"], 0.01)
    same("uplift all", round(100 * (rate(c) - rate(t)), 2), k["uplift_all_pts"], 0.01)
    for b in range(1, 6):
        up = 100 * (rate([r for r in c if r["baqaa_band"] == str(b)]) - rate([r for r in t if r["baqaa_band"] == str(b)]))
        same(f"band {b}", round(up, 2), k["by_band"][str(b)]["uplift_pts"], 0.01)
    show(f"churn {k['churn_control']}% without the offer, {k['churn_offered']}% with it: {k['uplift_all_pts']} pts; by band:",
         {b: v["uplift_pts"] for b, v in k["by_band"].items()})


@lab("2.2")
def lab_2_2():
    rs = trial()
    k = KEY["2.2"]
    for cell in k["cells"]:
        sub = [r for r in rs if r["contract"] == cell["contract"] and r["baqaa_band"] == str(cell["band"])]
        up = 100 * (rate([r for r in sub if r["offered"] == "0"]) - rate([r for r in sub if r["offered"] == "1"]))
        same(f"{cell['contract']} {cell['band']}", round(up, 2), cell["uplift_pts"], 0.01)
        show(f"{cell['contract']:16s} band {cell['band']}  n {cell['n']:6d}  churn {cell['churn_control']:5.2f} -> {cell['churn_offered']:5.2f}  uplift {cell['uplift_pts']:5.2f}")
    show("target (>= 3 pts):", k["target"], "| negative:", k["negative"])


@lab("2.3")
def lab_2_3():
    cells = rows("start/uplift_cells.csv")
    assert "50 ريالًا لكل عرض" in text("telecom/trial_note.txt")
    k = KEY["2.3"]
    def policy(sel):
        offers = kept = rev = 0.0
        for s in cells:
            if sel(s):
                n = int(s["customers_in_base"])
                offers += n
                kk = n * float(s["uplift_pts"]) / 100
                kept += kk
                rev += kk * float(s["avg_monthly_revenue_sar"]) * 12
        return offers, kept, rev - offers * 50
    for name, sel in [("all", lambda s: True), ("top_band", lambda s: s["baqaa_band"] == "5"),
                      ("uplift3", lambda s: float(s["uplift_pts"]) >= 3)]:
        o, kept, net = policy(sel)
        same(f"{name} offers", round(o), k[name]["offers"])
        same(f"{name} retained", round(kept), k[name]["retained"], 1)
        same(f"{name} net", round(net), k[name]["net"], 2)
        show(f"{name:9s} offers {k[name]['offers']:>7,}  retained {k[name]['retained']:>6,}  wasted {k[name]['wasted_pct']}%  net {k[name]['net']:>12,}")


@lab("2.4")
def lab_2_4():
    rs = rows("telecom/campaign_months.csv")
    k = KEY["2.4"]
    same("claimed", sum(int(r["offered_stayed"]) for r in rs), k["claimed_saved_total"])
    assert f"{k['claimed_saved_total']:,}" in text("telecom/campaign_report.txt")
    got = []
    for r in rs:
        if r["holdout"] != "0":
            up = int(r["offered_stayed"]) / int(r["offered"]) - int(r["holdout_stayed"]) / int(r["holdout"])
            got.append(dict(month=int(r["month"]), uplift_pts=round(100 * up, 2), incremental=round(up * int(r["offered"]))))
    same("measured", got, k["measured"])
    show(f"claimed {k['claimed_saved_total']:,} 'saved'; measured by month:", [(m["month"], m["uplift_pts"], m["incremental"]) for m in got])


def matches():
    inc = rows("network/incidents_week.csv")
    by = {}
    for i in inc:
        by.setdefault(i["site_id"], []).append(i)
    al = rows("network/alerts_week.csv")
    out = []
    for a in al:
        h = int(a["hour_of_week"])
        m = next((i["incident_id"] for i in by.get(a["site_id"], []) if int(i["start_hour"]) - 1 <= h <= int(i["end_hour"])), "")
        out.append((a, m))
    return inc, out


@lab("2.5")
def lab_2_5():
    inc, mt = matches()
    k = KEY["2.5"]
    t = 0.4
    sel = [(a, m) for a, m in mt if float(a["score"]) >= t]
    found = {m for a, m in sel if m}
    same("alerts at 0.4", len(sel), k["at_vendor"]["alerts"])
    same("precision", round(100 * sum(1 for a, m in sel if m) / len(sel), 2), k["at_vendor"]["precision"], 0.01)
    same("recall", round(100 * len(found) / len(inc), 2), k["at_vendor"]["recall"], 0.01)
    show(f"threshold 0.4: {k['at_vendor']['per_day']} alerts a day, precision {k['at_vendor']['precision']}%, recall {k['at_vendor']['recall']}%, missed {k['at_vendor']['missed']} of {k['incidents']}")
    assert "97%" in text("network/rasd_note.txt")


@lab("2.6")
def lab_2_6():
    al = rows("start/alert_matches.csv")
    best = rows("start/incident_best_score.csv")
    k = KEY["2.6"]
    for key, kv in k["table"].items():
        t = float(key[:3])
        skip = key.endswith("no_planned")
        sel = [a for a in al if float(a["score"]) >= t and not (skip and a["planned_work"] == "1")]
        same(f"{key} per day", round(len(sel) / 7, 2), kv["per_day"], 0.01)
        same(f"{key} precision", round(100 * sum(1 for a in sel if a["matched_incident"]) / len(sel), 2), kv["precision"], 0.01)
        same(f"{key} recall", round(100 * sum(float(b["best_alert_score"]) >= t for b in best) / len(best), 2), kv["recall"], 0.01)
        crit = [b for b in best if b["severity"] == "critical"]
        same(f"{key} critical", round(100 * sum(float(b["best_alert_score"]) >= t for b in crit) / len(crit), 2), kv["critical_recall"], 0.01)
        show(f"{key:15s} {kv['per_day']:7.2f}/day  precision {kv['precision']:6.2f}  recall {kv['recall']:6.2f}  critical {kv['critical_recall']:6.2f}")


@lab("2.7")
def lab_2_7():
    rs = rows("network/energy_pilot.csv")
    k = KEY["2.7"]
    def ch(g):
        sub = [r for r in rs if r["group"] == g]
        return 100 * (sum(float(r["kwh_per_day_after"]) for r in sub) / sum(float(r["kwh_per_day_before"]) for r in sub) - 1)
    same("pilot", round(ch("pilot"), 2), k["pilot_change_pct"], 0.01)
    same("did", round(ch("pilot") - ch("control"), 2), k["did_pct"], 0.02)
    over = [r["site_id"] for r in rs if r["group"] == "pilot" and float(r["drop_rate_after_pct"]) - float(r["drop_rate_before_pct"]) > 0.10]
    same("over guardrail", over, k["sites_over_guardrail"])
    req = text("network/location_request.txt")
    assert "أرقام جوالات" in req and "لا توجد" in req
    show(f"pilot {k['pilot_change_pct']}%, control {k['control_change_pct']}%, net {k['did_pct']}%; sites over the guardrail: {over}")


@lab("2.8")
def lab_2_8():
    guide = text("map/scoring_guide.txt")
    assert "2 × القيمة" in guide
    k = KEY["2.8"]
    def band(v):
        return 1 if v <= 0 else 2 if v < 100000 else 3 if v < 500000 else 4 if v < 2000000 else 5
    cap = {"trial": 5, "ab_test": 5, "pilot_with_control": 5, "backtest": 4, "offline_only": 3, "vendor_claim": 2, "not_measured": 2}
    harm = {"low": 5, "moderate": 3, "high": 1}
    rights = {"clear": 5, "partial": 3, "absent": 1}
    got = {}
    for u in rows("map/use_cases.csv"):
        v = min(band(float(u["measured_net_sar"])), cap[u["evidence"]])
        h, d = harm[u["customer_harm"]], rights[u["data_rights"]]
        q = "stop" if d == 1 or v == 1 else "pursue" if v >= 4 and h >= 3 else "fix_first" if v >= 4 else "test_cheaply"
        got[u["uc_id"]] = dict(value=v, harm=h, rights=d, total=2 * v + h + d, quadrant=q)
    same("scores", got, k["scores"])
    order = sorted(got, key=lambda x: (-got[x]["total"], x))
    same("ranking", order, k["ranking"])
    show("ranking:", [(x, got[x]["total"], got[x]["quadrant"]) for x in order])


def main(argv):
    ids = argv or list(RUN)
    failed = 0
    for i in ids:
        print(f"lab {i}")
        try:
            RUN[i]()
            print("    PASS")
        except AssertionError as e:
            failed += 1
            print("    FAIL", e)
    print(f"{len(ids) - failed} of {len(ids)} labs pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
