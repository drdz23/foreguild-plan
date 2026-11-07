# Foreguild: Buyers Are the Bottleneck

My entry to Seer's **FAO Operating Plan Contest** ([poidh base/1531](https://poidh.xyz/base/bounty/1531)). It is a revenue-first operating plan for Foreguild, a futarchy-governed AI job board.

- **Plan (HTML):** https://drdz23.github.io/foreguild-plan/
- **PDF:** https://drdz23.github.io/foreguild-plan/foreguild-operating-plan.pdf

The plan starts from data, not assumptions: every bounty on Verdikta Bounties (Base), the closest live AI-judged job board that pays in crypto. That is 394 on-chain bounties, 525 AI-jury verdicts and 61 outside buyers, from 12 Sep to 6 Nov 2026.

## Reproduce the numbers

```bash
python -I scripts/market_stats.py
```

This prints every Section 1 market figure from `data/jobs.json`.

| File | What it is |
|---|---|
| `data/jobs.json` | Public `GET https://bounties.verdikta.org/api/jobs/<id>` for ids 1–469, pulled 7 Nov 2026 |
| `scripts/pull_jobs.mjs` | Re-pulls that dataset |
| `scripts/market_stats.py` | Section 1 market numbers: demand split, speed, concentration, evaluation cost |
| `scripts/audit.py`, `scripts/pull_rubrics.mjs` | Rubric preflight back-test of the platform's own bounties |
| `data/audit_summary.json`, `data/audit_inhouse.csv` | Output of `audit.py` |

`audit.py` imports the open-source linter [drdz23/verdikta-rubric-preflight](https://github.com/drdz23/verdikta-rubric-preflight). It also expects the rubrics fetched from IPFS by `pull_rubrics.mjs`.

## Disclosure

I am an active hunter on Verdikta Bounties, the board analysed here. I have no affiliation with Seer or Verdikta. The plan was drafted with an AI assistant (Claude), and every number was recomputed from the public data above.
