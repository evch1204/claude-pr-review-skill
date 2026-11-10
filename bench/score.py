#!/usr/bin/env python3
"""Turn blind grader output into per-run grading.json files and a comparison table.

usage: score.py <iteration_dir> <grading_dir>
  <grading_dir>/<case>/grades.json   grader output keyed by blind label (A, B, ...)
  <grading_dir>/<case>.map.json      blind label -> configuration
Answer keys come from bench/fixtures/<case>/answer_key.json or bench/real_answer_keys/<case>.json.
"""
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
WEIGHT = {"blocker": 3, "major": 2, "minor": 1}
CONFIG_ORDER = ["with_skill", "old_skill", "anthropic_code_review", "spillwave", "without_skill"]


def answer_key(case):
    p = BENCH / "fixtures" / case / "answer_key.json"
    return json.loads((p if p.exists() else BENCH / "real_answer_keys" / f"{case}.json").read_text())


def assertions(key, g):
    out = []
    for issue in key["issues"]:
        r = g["issues"].get(issue["id"], {})
        sev = r.get("severity_given", "none")
        out.append({
            "text": f"Catches [{issue['severity']}] {issue['id']}",
            "passed": bool(r.get("found")),
            "evidence": f"({sev}) {r.get('evidence', '')}".strip(),
        })
    blockers = [i for i in key["issues"] if i["severity"] == "blocker"]
    if blockers:
        ok = all(g["issues"].get(i["id"], {}).get("found") and g["issues"][i["id"]].get("severity_given") == "blocking" for i in blockers)
        out.append({"text": "Rates every answer-key blocker as blocking", "passed": ok,
                    "evidence": ", ".join(f"{i['id']}={g['issues'].get(i['id'], {}).get('severity_given', 'none')}" for i in blockers)})
    for d in key.get("decoys", []):
        if d["id"] == "clean-pr":
            continue
        r = g.get("decoys", {}).get(d["id"], {})
        out.append({"text": f"Does not flag decoy: {d['id']}", "passed": not r.get("flagged"), "evidence": r.get("evidence", "")})
    exp = key["expected_verdict"]
    ok = g["verdict"] in (("approve", "approve_with_comments") if exp == "approve" else (exp,))
    out.append({"text": f"Verdict is {exp}", "passed": ok, "evidence": f"review verdict: {g['verdict']}"})
    serious_fp = [f for f in g.get("false_positives", []) if f.get("severity_given") in ("blocking", "should_fix")]
    out.append({"text": "No false positives rated should-fix or higher", "passed": not serious_fp,
                "evidence": "; ".join(f"{f['claim']} — {f['why_wrong']}" for f in serious_fp)})
    if exp == "approve":
        out.append({"text": "At most 3 nits on a clean PR", "passed": g.get("nit_count", 0) <= 3, "evidence": f"{g.get('nit_count')} nits"})
    return out


def main():
    it_dir, grading_dir = Path(sys.argv[1]), Path(sys.argv[2])
    rows = {}
    for gfile in sorted(grading_dir.glob("*/grades.json")):
        case = gfile.parent.name
        key = answer_key(case)
        mapping = json.loads((grading_dir / f"{case}.map.json").read_text())
        grades = json.loads(gfile.read_text())
        total_w = sum(WEIGHT[i["severity"]] for i in key["issues"])
        for label, cfg in mapping.items():
            g = grades[label]
            exp = assertions(key, g)
            passed = sum(e["passed"] for e in exp)
            run = it_dir / case / cfg
            timing = json.loads((run / "timing.json").read_text()) if (run / "timing.json").exists() else {}
            review = (run / "outputs" / "review.md").read_text()
            (run / "grading.json").write_text(json.dumps({
                "expectations": exp,
                "summary": {"passed": passed, "failed": len(exp) - passed, "total": len(exp), "pass_rate": round(passed / len(exp), 2)},
                "timing": {"total_duration_seconds": timing.get("total_duration_seconds")},
                "grader": {k: g[k] for k in ("false_positives", "valid_extras", "nit_count", "actionability", "notes") if k in g},
            }, indent=2))
            found_w = sum(WEIGHT[i["severity"]] for i in key["issues"] if g["issues"].get(i["id"], {}).get("found"))
            rows.setdefault(cfg, {})[case] = {
                "pass_rate": passed / len(exp),
                "recall_w": found_w / total_w if total_w else None,
                "found": sum(bool(g["issues"].get(i["id"], {}).get("found")) for i in key["issues"]),
                "n_issues": len(key["issues"]),
                "fp": len(g.get("false_positives", [])),
                "decoy_hits": sum(bool(v.get("flagged")) for k, v in g.get("decoys", {}).items() if k != "clean-pr"),
                "verdict_ok": next(e["passed"] for e in exp if e["text"].startswith("Verdict")),
                "nits": g.get("nit_count", 0),
                "action": g.get("actionability"),
                "words": len(review.split()),
                "tokens": timing.get("total_tokens"),
                "secs": timing.get("total_duration_seconds"),
            }

    cases = sorted({c for r in rows.values() for c in r})
    cfgs = [c for c in CONFIG_ORDER if c in rows]
    lines = ["# Benchmark comparison", "",
             "Recall is weighted by severity (blocker 3, major 2, minor 1). FP = findings the blind grader checked against the code and judged wrong.", ""]
    lines += ["## Overall", "", "| Reviewer | Pass rate | Weighted recall | Bugs found | False positives | Decoys flagged | Verdict correct | Actionability (1-5) | Avg words | Avg tokens | Avg time (s) |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for cfg in cfgs:
        rs = [rows[cfg][c] for c in cases if c in rows[cfg]]
        rec = [r["recall_w"] for r in rs if r["recall_w"] is not None]
        avg = lambda k: sum(r[k] for r in rs if r[k] is not None) / max(1, sum(r[k] is not None for r in rs))
        lines.append(f"| {cfg} | {avg('pass_rate'):.0%} | {sum(rec)/len(rec):.0%} | {sum(r['found'] for r in rs)}/{sum(r['n_issues'] for r in rs)} | "
                     f"{sum(r['fp'] for r in rs)} | {sum(r['decoy_hits'] for r in rs)} | {sum(r['verdict_ok'] for r in rs)}/{len(rs)} | "
                     f"{avg('action'):.1f} | {avg('words'):.0f} | {avg('tokens'):.0f} | {avg('secs'):.0f} |")
    for case in cases:
        lines += ["", f"## {case}", "", "| Reviewer | Pass rate | Found | Weighted recall | FP | Decoys | Verdict ok | Nits | Words | Tokens | Time (s) |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for cfg in cfgs:
            r = rows[cfg].get(case)
            if not r:
                continue
            rec = "n/a" if r["recall_w"] is None else f"{r['recall_w']:.0%}"
            lines.append(f"| {cfg} | {r['pass_rate']:.0%} | {r['found']}/{r['n_issues']} | {rec} | {r['fp']} | {r['decoy_hits']} | "
                         f"{'✅' if r['verdict_ok'] else '❌'} | {r['nits']} | {r['words']} | {r['tokens']} | {r['secs']} |")
    (it_dir / "comparison.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
