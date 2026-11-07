"""
audit.py - Deliverable 1 of the "Verdikta Bounty Portfolio Audit and Rubric Repair Pack".

Audits every bounty created by Verdikta's own creator wallets (W0, W2, W3):
  * runs rubric_preflight.check() on each bounty's published rubric with its real threshold
  * joins the outcome (awarded to an external hunter, self-awarded test, expired with no
    winner, cancelled, orphaned, open), jury statistics, window length and locked ETH
  * ranks every bounty by risk and back-tests whether preflight HIGH findings predicted failure

Inputs (all public data):
  data/jobs.json                         /api/jobs/<id> for every job (pull_jobs.mjs)
  ../392/work/rubrics/<id>.json          rubric JSON from IPFS (rubricCid); job.rubricContent used when present
  ../393_subir/verdikta_submissions.csv  per-submission jury analysis for bounties 1-391 (#393 dataset)
Outputs:
  out/audit_inhouse.csv, out/audit_summary.json
Run:  python -I audit.py
"""
import csv, json, os, sys, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "verdikta-rubric-preflight"))
import rubric_preflight as pf  # our own checker (github.com/drdz23/verdikta-rubric-preflight)

WALLETS = {
    "0xf6dd9256d0091c6e773ebfdfc79783f9663e65fc": "W0",
    "0xb7dfc99fee12759531558819dc400e27fa0b57de": "W2",
    "0x237d9a1bcb961a3e8c1441a2500265df0c0d5609": "W3",
}
lc = lambda s: (s or "").lower()


def load_rubric(job):
    rc = job.get("rubricContent")
    if isinstance(rc, str):
        try:
            rc = json.loads(rc)
        except Exception:
            rc = None
    if isinstance(rc, dict) and rc.get("criteria"):
        return rc, "rubricContent"
    p = os.path.join(HERE, "..", "392", "work", "rubrics", f"{job['jobId']}.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8")), "ipfs"
        except Exception:
            pass
    p = os.path.join(HERE, "data", "rubrics", f"{job['jobId']}.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8")), "ipfs"
    return None, "missing"


def passed(s):
    return "APPROVED" in (s.get("status") or "") or "Passed" in (s.get("onChainStatus") or "")


def outcome(job):
    st = (job.get("status") or "").upper()
    win = lc(job.get("winner"))
    if st == "AWARDED" or win:
        if win and win in WALLETS:
            return "AWARDED_SELF"          # creator's own wallet won: a test, no market signal
        if win and win == lc(job.get("creator")):
            return "AWARDED_SELF"
        return "AWARDED_EXTERNAL"
    if "ORPHAN" in st or job.get("orphanReason"):
        return "ORPHANED"
    if st == "CANCELLED":
        return "CANCELLED"
    if st == "OPEN":
        return "OPEN"
    if st in ("CLOSED", "EXPIRED", "FAILED"):
        return "EXPIRED_NO_WINNER"
    return st or "UNKNOWN"


def main():
    jobs = json.load(open(os.path.join(HERE, "data", "jobs.json"), encoding="utf-8"))
    subcsv = collections.defaultdict(list)
    p = os.path.join(HERE, "..", "393_subir", "verdikta_submissions.csv")
    for r in csv.DictReader(open(p, encoding="utf-8")):
        subcsv[int(r["bountyId"])].append(r)

    # The API answers some missing ids with a neighbouring job (e.g. /jobs/398 -> jobId 397): dedupe by jobId.
    uniq = {}
    for job in jobs.values():
        if job.get("jobId") is not None:
            uniq[int(job["jobId"])] = job
    rows = []
    for jid0, job in sorted(uniq.items()):
        w = WALLETS.get(lc(job.get("creator")))
        if not w:
            continue
        jid = int(job["jobId"])
        thr = job.get("threshold")
        thr = float(thr) if thr not in (None, "") else None
        rub, src = load_rubric(job)
        res = pf.check(rub, threshold=thr) if rub else {"task_type": pf.classify(job.get("title", ""), job.get("description", "")), "gates": None, "findings": []}
        f = [x for x in res["findings"] if x["level"] in ("HIGH", "MEDIUM")]
        highs = sorted({x["rule"] for x in f if x["level"] == "HIGH"})
        meds = sorted({x["rule"] for x in f if x["level"] == "MEDIUM"})
        subs = job.get("submissions") or []
        ev = [s for s in subs if s.get("score") is not None or any(t in (s.get("status") or "") for t in ("APPROVED", "REJECTED"))]
        scores = [float(s["score"]) for s in ev if s.get("score") not in (None, "") and not (passed(s) and float(s["score"]) == 0)]
        ext_subs = [s for s in subs if lc(s.get("hunter")) not in WALLETS]
        a = subcsv.get(jid, [])
        split = sum(1 for r in a if r.get("splitJury") == "1")
        gatefail = sum(1 for r in a if r.get("jurorsFailingGate") not in ("", "0", None))
        o_open, o_close = job.get("submissionOpenTime"), job.get("submissionCloseTime")
        win_h = round((o_close - o_open) / 3600, 1) if o_open and o_close else None
        oc = outcome(job)
        created = datetime.datetime.fromtimestamp(job["createdAt"], datetime.timezone.utc).strftime("%Y-%m-%d") if job.get("createdAt") else ""
        amt = float(job.get("bountyAmount") or 0)
        rows.append({
            "bountyId": jid, "wallet": w, "created": created, "title": (job.get("title") or "")[:110],
            "status": job.get("status"), "outcome": oc, "prizeEth": amt, "threshold": thr,
            "windowHours": win_h, "taskType": res["task_type"], "gates": res.get("gates"),
            "rubricSource": src, "nHigh": len(highs), "highRules": ";".join(highs),
            "nMedium": len(meds), "mediumRules": ";".join(meds),
            "submissions": len(subs), "externalSubmissions": len(ext_subs), "juryScored": len(ev),
            "passedSubs": sum(1 for s in ev if passed(s)), "bestScore": max(scores) if scores else "",
            "bestScoreGap": round(thr - max(scores), 2) if scores and thr is not None else "",
            "splitJuryRejections": split, "rejectionsWithGateFail": gatefail,
            "lockedEthNoWinner": amt if oc in ("EXPIRED_NO_WINNER", "OPEN") else 0,
        })

    # ---- risk score (transparent, additive) ----
    for r in rows:
        s = 3 * r["nHigh"] + r["nMedium"]
        if r["threshold"] is not None and r["threshold"] >= 94: s += 2
        # (No window-length penalty: all 21 market bounties with a <=24 h window were awarded.)
        r["riskScore"] = s   # rubric/launch properties only; the outcome is NOT used, so the back-test is fair
        r["observedFailure"] = int(r["outcome"] == "EXPIRED_NO_WINNER" and r["externalSubmissions"] > 0)
        r["riskTier"] = "RED" if s >= 7 else "AMBER" if s >= 3 else "GREEN"

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    cols = list(rows[0].keys())
    with open(os.path.join(HERE, "out", "audit_inhouse.csv"), "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=cols)
        wr.writeheader()
        for r in sorted(rows, key=lambda r: (-r["riskScore"], r["bountyId"])):
            wr.writerow(r)

    # ---- summary + back-test ----
    C = collections.Counter
    market = [r for r in rows if r["outcome"] in ("AWARDED_EXTERNAL", "EXPIRED_NO_WINNER") and r["externalSubmissions"] > 0]
    def rate(group):
        g = list(group)
        return {"n": len(g), "awarded": sum(r["outcome"] == "AWARDED_EXTERNAL" for r in g),
                "awardRate": round(sum(r["outcome"] == "AWARDED_EXTERNAL" for r in g) / len(g), 3) if g else None}
    rule_counts = C(rule for r in rows for rule in r["highRules"].split(";") if rule)
    by_rule = {rule: rate(r for r in market if rule in r["highRules"].split(";")) for rule in rule_counts}
    fails = [r for r in rows if r["observedFailure"]]
    def would_pass_at(r, t):
        return r["bestScore"] != "" and r["threshold"] is not None and r["threshold"] > t and float(r["bestScore"]) >= t
    win_window = lambda f: rate(r for r in market if r["windowHours"] is not None and f(r["windowHours"]))
    summary = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "jobsInDataset": len(uniq), "inhouseBounties": len(rows),
        "byWallet": dict(C(r["wallet"] for r in rows)),
        "byOutcome": dict(C(r["outcome"] for r in rows)),
        "byTier": dict(C(r["riskTier"] for r in rows)),
        "rubricSource": dict(C(r["rubricSource"] for r in rows)),
        "highRuleFrequency": dict(rule_counts.most_common()),
        "ethPrizeTotal": round(sum(r["prizeEth"] for r in rows), 4),
        "ethAwardedExternal": round(sum(r["prizeEth"] for r in rows if r["outcome"] == "AWARDED_EXTERNAL"), 4),
        "ethExpiredNoWinner": round(sum(r["prizeEth"] for r in rows if r["outcome"] == "EXPIRED_NO_WINNER"), 4),
        "ethLockedOpenNow": round(sum(r["prizeEth"] for r in rows if r["outcome"] == "OPEN"), 4),
        "window24h": sum(1 for r in rows if r["windowHours"] is not None and r["windowHours"] <= 24.5),
        "backtest_note": "Market bounties = in-house bounties with >=1 external submission that ended AWARDED_EXTERNAL or EXPIRED_NO_WINNER. "
                         "The preflight thresholds were calibrated on this same history (bounties 1-391), so this is an in-sample consistency check, not an out-of-sample validation.",
        "failures": {
            "n": len(fails),
            "withAtLeastOneHigh": sum(1 for r in fails if r["nHigh"] >= 1),
            # Open-problem math is excluded: a high threshold there is deliberate (it guards against flawed proofs).
            "wouldHaveBeenAwardedAtThreshold89": [r["bountyId"] for r in fails if would_pass_at(r, 89) and r["taskType"] != "math_open_problem"],
            "ids": [r["bountyId"] for r in fails],
        },
        "orphanedInhouse": {"n": sum(r["outcome"] == "ORPHANED" for r in rows),
                            "eth": round(sum(r["prizeEth"] for r in rows if r["outcome"] == "ORPHANED"), 4)},
        "windowEffect": {"le24h": win_window(lambda h: h <= 24.5), "gt24h": win_window(lambda h: h > 24.5)},
        "backtest": {
            "allMarket": rate(market),
            "noHigh": rate(r for r in market if r["nHigh"] == 0),
            "oneHigh": rate(r for r in market if r["nHigh"] == 1),
            "twoPlusHigh": rate(r for r in market if r["nHigh"] >= 2),
            "byTier": {t: rate(r for r in market if r["riskTier"] == t) for t in ("GREEN", "AMBER", "RED")},
            "byHighRule": by_rule,
        },
    }
    json.dump(summary, open(os.path.join(HERE, "out", "audit_summary.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
