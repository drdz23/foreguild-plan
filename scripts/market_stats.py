"""Reproduces the Section 1 market numbers of the Foreguild plan from data/jobs.json.
Run:  python -I scripts/market_stats.py"""
import json, os, collections, statistics as st, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "..", "data", "jobs.json"), encoding="utf-8"))
jobs = {int(v["jobId"]): v for v in d.values() if v.get("jobId") is not None}  # API aliases missing ids: dedupe
PLATFORM = {"0xf6dd9256d0091c6e773ebfdfc79783f9663e65fc", "0xb7dfc99fee12759531558819dc400e27fa0b57de",
            "0x237d9a1bcb961a3e8c1441a2500265df0c0d5609"}
lc = lambda s: (s or "").lower()
on = [j for j in jobs.values() if j.get("status") != "ORPHANED"]
side = lambda j: "platform" if lc(j.get("creator")) in PLATFORM else "outside"
ts = [j["createdAt"] for j in on if j.get("createdAt")]
day = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d")
print("jobs", len(jobs), "on-chain", len(on), "span", day(min(ts)), "->", day(max(ts)))
n, eth, aw, aweth = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
for j in on:
    s, a, w = side(j), float(j.get("bountyAmount") or 0), lc(j.get("winner"))
    n[s] += 1; eth[s] += a
    if w and w not in PLATFORM and w != lc(j.get("creator")):
        aw[s] += 1; aweth[s] += a
print("bounties", dict(n), "eth", {k: round(v, 4) for k, v in eth.items()})
print("paid to outside worker", dict(aw), {k: round(v, 4) for k, v in aweth.items()})
cc = collections.Counter(lc(j["creator"]) for j in on if side(j) == "outside")
hunters = {lc(s.get("hunter")) for j in on for s in (j.get("submissions") or [])}
print("outside creators", len(cc), "largest", cc.most_common(1)[0][1],
      "creators who are also workers", sum(c in hunters for c in cc), "their bounties", sum(v for c, v in cc.items() if c in hunters))
tta, subs = [], []
for j in on:
    ss = j.get("submissions") or []; subs.append(len(ss)); w = lc(j.get("winner"))
    if w and w not in PLATFORM:
        t = [s["submittedAt"] for s in ss if lc(s.get("hunter")) == w and s.get("submittedAt")]
        if t and j.get("submissionOpenTime"):
            h = (min(t) - j["submissionOpenTime"]) / 3600
            if h >= 0: tta.append(h)
print("winning submission: median min", round(st.median(tta) * 60, 1), "share <1h", round(sum(x < 1 for x in tta) / len(tta), 2))
print("submissions per bounty median", st.median(subs), "mean", round(st.mean(subs), 2))
wc = collections.Counter(lc(j.get("winner")) for j in on if lc(j.get("winner")) and lc(j.get("winner")) not in PLATFORM)
top = wc.most_common(2); print("outside awards", sum(wc.values()), "distinct winners", len(wc), "top-2 share", round((top[0][1] + top[1][1]) / sum(wc.values()), 2))
sc = [s for j in on for s in (j.get("submissions") or []) if s.get("score") not in (None, "")]
print("scored submissions", len(sc), "passed", sum("APPROVED" in (s.get("status") or "") for s in sc))
b = [float(s["ethMaxBudget"]) / (1e18 if float(s["ethMaxBudget"]) > 1e6 else 1) for j in on for s in (j.get("submissions") or []) if s.get("ethMaxBudget")]
pr = [float(j["bountyAmount"]) for j in on if j.get("bountyAmount")]
print("evaluation prepay median ETH", st.median(b), "prize mean ETH", round(st.mean(pr), 4), "eval share of mean task", round(1.59 * st.median(b) / st.mean(pr), 3))
