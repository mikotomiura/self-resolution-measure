#!/usr/bin/env python3
"""Outcome-agnostic vs outcome-requiring self-resolution measures on two public datasets.

    python analysis/analyze.py --out results          # gates, then all results
    python analysis/analyze.py --selftest             # do the gates and controls bite?

Definitions: config.json (frozen before results were computed; see NOTES.md).
Standard library only.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import d1  # noqa: E402
import d2  # noqa: E402
from stats import Unit, counts, measures_from_counts, cluster_bootstrap, summarise  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESOLVED_SETS = {"DF1": ("DF1",), "DF1+DF2": ("DF1", "DF2")}


def load_config() -> tuple[dict, str]:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    seed = (ROOT / cfg["seed_file"]).read_text(encoding="utf-8").strip()
    return cfg, seed


def clean(x):
    """Round floats and turn NaN into null so that the JSON is stable and valid."""
    if isinstance(x, float):
        return None if math.isnan(x) else round(x, 6)
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return x


# ---------------------------------------------------------------------------
# D1
# ---------------------------------------------------------------------------
def run_d1(cfg: dict, seed: str, sessions: list) -> tuple[dict, list[dict]]:
    c1 = cfg["d1"]
    diag: dict = {}
    episodes = d1.build_episodes(sessions, diag)
    checks = d1.gate_v1(episodes, diag, c1["gate_v1"])
    if not all(c["ok"] for c in checks):
        return {}, checks

    boot = cfg["bootstrap"]
    results = {}
    for mode in d1.CONSULT_MODES:
        for rlabel, rcodes in RESOLVED_SETS.items():
            units = d1.to_units(episodes, mode, rcodes)
            results[f"{mode}|{rlabel}"] = summarise(units, boot["replicates"],
                                                     f"{seed}:d1:{mode}:{rlabel}", boot["level"])
    out = {
        "primary": f"{c1['consultation']['primary']}|DF1",
        "results": results,
        "strata_by_origin": {m: d1.strata(episodes, m, ("DF1",)) for m in d1.CONSULT_MODES},
        "reproduce_emse2023": d1.reproduce_emse(episodes, c1["reproduce_emse2023"],
                                                c1["short_long_quartile"]["short_n"],
                                                c1["short_long_quartile"]["long_n"]),
        "outcome_codes": _outcome_codes(episodes),
        "developers": len({e["cluster"] for e in episodes}),
    }
    return out, checks


def _outcome_codes(episodes: list[dict]) -> dict:
    tally: dict[str, int] = {}
    for ep in episodes:
        codes = sorted(d1.last_codes(ep) & d1.DF_OUTCOME)
        key = "DF" + "/".join(map(str, codes)) if codes else "none"
        tally[key] = tally.get(key, 0) + 1
    return dict(sorted(tally.items()))


# ---------------------------------------------------------------------------
# D2
# ---------------------------------------------------------------------------
def run_d2(cfg: dict, seed: str) -> tuple[dict, list[dict], list[str]]:
    c2 = cfg["d2"]
    a_path, b_path = (ROOT / p for p in c2["transcriptions"])
    rows_a, rows_b = d2.read_rows(a_path), d2.read_rows(b_path)
    diffs = d2.compare(rows_a, rows_b)
    if diffs:
        return {}, [], diffs
    text_ids = d2.read_text_external(ROOT / c2["text_external"])
    checks = d2.gate(rows_a, text_ids, c2["gate"])
    if not all(c["ok"] for c in checks):
        return {}, checks, []

    boot = cfg["bootstrap"]
    results = {}
    for mode in d2.CONSULT_MODES:
        units = d2.to_units(rows_a, mode, text_ids)
        results[mode] = summarise(units, boot["replicates"], f"{seed}:d2:{mode}", boot["level"])
    streamer_min = sum(int(r["task_time_min"]) for r in rows_a if r["group"] == "streamer")
    out = {
        "primary": c2["consultation"]["primary"],
        "results": results,
        "text_described_tasks": sorted(text_ids),
        "report_only": {
            "streamer_minutes_table4": streamer_min,
            "streamer_hours_stated": c2["report_only"]["streamer_hours"]["value"],
            "total_minutes_table4": sum(int(r["task_time_min"]) for r in rows_a),
        },
        "developers": len({r["developer_id"] for r in rows_a}),
    }
    return out, checks, []


# ---------------------------------------------------------------------------
# Self-test: gates must turn red on absent / broken input; controls must recover truth
# ---------------------------------------------------------------------------
def _t(sec: int) -> str:
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def synthetic_sessions(rf: int, rc: int, uf: int, uc: int) -> list:
    """rf/rc = resolved without/with consultation; uf/uc = unresolved without/with.

    The first resolved-without-consultation episode is split by an interruption
    (DF4 ... DF7) so the control also exercises the merge step.
    """
    kinds = ["rf"] * rf + ["rc"] * rc + ["uf"] * uf + ["uc"] * uc
    sessions = []
    for s_idx in range(0, len(kinds), 10):
        anns, t = [], 10
        for j, kind in enumerate(kinds[s_idx:s_idx + 10]):
            outcome = "DF1" if kind[0] == "r" else "DF3"
            subs = [{"title": "Testing the program and reading the outputs", "description": "O2",
                     "duration": {"start": {"time": _t(t)}, "end": {"time": _t(t + 5)}}}]
            if kind[1] == "c":
                subs.append({"title": d1.SEEKING, "description": "U1 U6",
                             "duration": {"start": {"time": _t(t + 5)}, "end": {"time": _t(t + 20)}}})
            if s_idx == 0 and j == 0 and kind == "rf":
                anns.append({"title": "Debugging", "description": "DF6 DF4 DF9", "subAnnotations": subs,
                             "duration": {"start": {"time": _t(t)}, "end": {"time": _t(t + 30)}}})
                anns.append({"title": "Development", "description": "",
                             "duration": {"start": {"time": _t(t + 30)}, "end": {"time": _t(t + 60)}}})
                anns.append({"title": "Debugging", "description": f"DF7 {outcome}", "subAnnotations": [],
                             "duration": {"start": {"time": _t(t + 60)}, "end": {"time": _t(t + 90)}}})
                t += 100
                continue
            anns.append({"title": "Debugging", "description": f"DF6 {outcome} DF9", "subAnnotations": subs,
                         "duration": {"start": {"time": _t(t)}, "end": {"time": _t(t + 30)}}})
            t += 40
        sessions.append({"id": f"s{s_idx}", "githubURL": f"dev{s_idx // 20}", "annotations": anns[::-1]})
    return sessions


def selftest(cfg: dict, seed: str, sessions: list) -> int:
    failures = []

    def expect(name: str, ok: bool, detail: str = "") -> None:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}{(' -- ' + detail) if detail else ''}")
        if not ok:
            failures.append(name)

    g = cfg["d1"]["gate_v1"]
    print("D1 gate")
    diag: dict = {}
    checks = d1.gate_v1(d1.build_episodes(sessions, diag), diag, g)
    expect("normal data: every item green", all(c["ok"] for c in checks), f"{len(checks)} items")

    stripped = copy.deepcopy(sessions)
    for s in stripped:
        for a in s["annotations"]:
            a["subAnnotations"] = [x for x in (a.get("subAnnotations") or []) if x.get("title") != d1.SEEKING]
    diag = {}
    red = [c["name"] for c in d1.gate_v1(d1.build_episodes(stripped, diag), diag, g) if not c["ok"]]
    expect("absent: consultations removed -> gate red", bool(red), f"{len(red)} red")

    diag = {}
    eps = d1.build_episodes(sessions, diag, merge=False)
    red = [c["name"] for c in d1.gate_v1(eps, diag, g) if not c["ok"]]
    expect("broken: merge disabled -> gate red", bool(red) and len(eps) == 109,
           f"episodes={len(eps)}, {len(red)} red")

    print("D2 transcription and gate")
    c2 = cfg["d2"]
    rows_a = d2.read_rows(ROOT / c2["transcriptions"][0])
    b_path = ROOT / c2["transcriptions"][1]
    rows_b = d2.read_rows(b_path) if b_path.exists() else []
    expect("normal: transcriptions A and B agree", b_path.exists() and not d2.compare(rows_a, rows_b),
           "B missing" if not b_path.exists() else f"{len(d2.compare(rows_a, rows_b))} diffs")
    tampered = copy.deepcopy(rows_a)
    tampered[4]["resolved"] = "Y" if tampered[4]["resolved"] == "N" else "N"
    expect("broken: one flipped cell is detected", len(d2.compare(rows_a, tampered)) == 1)
    text_ids = d2.read_text_external(ROOT / c2["text_external"])
    expect("normal: D2 gate green", all(c["ok"] for c in d2.gate(rows_a, text_ids, c2["gate"])))
    red = [c["name"] for c in d2.gate(tampered, text_ids, c2["gate"]) if not c["ok"]]
    expect("broken: flipped Resolved -> D2 gate red", bool(red), f"{len(red)} red")

    print("Controls (synthetic, through the full D1 path)")
    eps = d1.build_episodes(synthetic_sessions(60, 10, 20, 10))
    m = measures_from_counts(counts(d1.to_units(eps, "strict", ("DF1",))))
    want = {"R0": 0.80, "R1": 60 / 70, "R0_prime": 0.60, "numerator_effect": 0.20,
            "denominator_effect": 0.80 - 60 / 70}
    expect("positive: known 2x2 recovered exactly (incl. one merged episode)",
           len(eps) == 100 and all(abs(m[k] - v) < 1e-12 for k, v in want.items()),
           f"episodes={len(eps)} " + ", ".join(f"{k}={m[k]:.4f}" for k in want))
    eps = d1.build_episodes(synthetic_sessions(70, 30, 0, 0))
    m = measures_from_counts(counts(d1.to_units(eps, "strict", ("DF1",))))
    expect("negative: nothing unresolved -> numerator effect 0, R0 == R0'",
           m["numerator_effect"] == 0 and m["R0"] == m["R0_prime"])

    print("Bootstrap")
    one = [Unit("only", r, c) for r, c in [(True, False)] * 6 + [(False, False)] * 2 + [(True, True)] * 2]
    b = cluster_bootstrap(one, 200, "t")
    p = measures_from_counts(counts(one))
    expect("single cluster -> interval collapses to the point",
           all(abs(b["intervals"][k][0] - p[k]) < 1e-12 and abs(b["intervals"][k][1] - p[k]) < 1e-12
               for k in p))
    many = [Unit(f"c{i % 7}", i % 3 != 0, i % 5 == 0) for i in range(70)]
    expect("same seed label -> identical intervals",
           cluster_bootstrap(many, 500, "x") == cluster_bootstrap(many, 500, "x"))

    print(f"selftest: {'OK' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}"


def ci(pair) -> str:
    return "n/a" if not pair or pair[0] is None else f"[{pct(pair[0])}, {pct(pair[1])}]"


def result_rows(results: dict) -> list[str]:
    lines = ["| definition | n | R0 | R1 | R0′ | R0 − R0′ (bootstrap 95%) | R0 − R1 (bootstrap 95%) |",
             "|---|---|---|---|---|---|---|"]
    for key, r in results.items():
        c, p, bi = r["counts"], r["point"], r["cluster_bootstrap"]["intervals"]
        lines.append(
            f"| {key} | {c['n']} | {pct(p['R0'])} ({c['no_consult']}/{c['n']}) "
            f"| {pct(p['R1'])} ({c['resolved_no_consult']}/{c['resolved']}) "
            f"| {pct(p['R0_prime'])} ({c['resolved_no_consult']}/{c['n']}) "
            f"| **{pct(p['numerator_effect'])}** ({r['unresolved_no_consult']}/{c['n']}) {ci(bi['numerator_effect'])} "
            f"| {pct(p['denominator_effect'])} {ci(bi['denominator_effect'])} |")
    return lines


def write_report(path: Path, m: dict) -> None:
    L = ["# Results", "",
         "Generated by `run.sh`. Percentages; bootstrap intervals resample developers "
         f"({m['bootstrap']['replicates']} replicates, seed `{m['seed']}`).", ""]
    L += ["## Gates", ""]
    for name in ("d1_gate_v1", "d2_gate"):
        ok = sum(c["ok"] for c in m[name])
        L.append(f"- {name}: {ok}/{len(m[name])} green")
    L += ["- D2 transcriptions A and B: identical", ""]

    d = m["d1"]
    L += ["## D1 — Alaboudi & LaToza (episodes; developers = "
          f"{d['developers']}; primary `{d['primary']}`)", ""]
    L += result_rows(d["results"]) + [""]
    L += ["Outcome codes at episode end: " + ", ".join(f"{k} {v}" for k, v in d["outcome_codes"].items()), ""]
    L += ["### By defect origin (resolved = DF1)", "",
          "| consultation | origin | n | consulted among resolved | consulted among unresolved | R0 − R0′ |",
          "|---|---|---|---|---|---|"]
    for mode, st in d["strata_by_origin"].items():
        for origin, s in st.items():
            a, b = s["consulted_among_resolved"], s["consulted_among_unresolved"]
            L.append(f"| {mode} | {origin} | {s['counts']['n']} | {a[0]}/{a[1]} | {b[0]}/{b[1]} "
                     f"| {pct(s['point']['numerator_effect'])} |")
    L += ["", "### Can the EMSE 2023 figures be reproduced from the shared public coding?", "",
          "| item | reported | " + " | ".join(d["reproduce_emse2023"]) + " |",
          "|---|---|" + "---|" * len(d["reproduce_emse2023"])]
    items = [r["item"] for r in next(iter(d["reproduce_emse2023"].values()))["rows"]]
    for i, item in enumerate(items):
        cells = []
        for mode, rep in d["reproduce_emse2023"].items():
            r = rep["rows"][i]
            cells.append(f"{r['observed_text']} {'✓' if r['match'] else '✗'}")
        reported = d["reproduce_emse2023"]["strict"]["rows"][i]["reported"]
        L.append(f"| {item} | {reported} | " + " | ".join(cells) + " |")
    L.append("| matched | | " + " | ".join(f"{rep['matched']}/{rep['items']}"
                                          for rep in d["reproduce_emse2023"].values()) + " |")

    e = m["d2"]
    L += ["", f"## D2 — Li & Coblenz (tasks; developers = {e['developers']}; primary `{e['primary']}`)", ""]
    L += result_rows(e["results"]) + [""]
    L += [f"Text-described consultations added in `table5_plus_text`: {', '.join(e['text_described_tasks'])}.", ""]
    ro = e["report_only"]
    L += [f"Report only: Table 4 streamer tasks sum to {ro['streamer_minutes_table4']} min "
          f"({ro['streamer_minutes_table4'] / 60:.2f} h) against {ro['streamer_hours_stated']} h stated in Sec. 4; "
          f"all tasks sum to {ro['total_minutes_table4']} min ({ro['total_minutes_table4'] / 60:.2f} h).", ""]
    path.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    cfg, seed = load_config()
    sessions = json.loads((ROOT / cfg["d1"]["input"]).read_text(encoding="utf-8"))
    if args.selftest:
        return selftest(cfg, seed, sessions)

    d1_out, d1_checks = run_d1(cfg, seed, sessions)
    for c in d1_checks:
        if not c["ok"]:
            print(f"D1 gate red: {c['name']} observed={c['observed']} expected={c['expected']}")
    d2_out, d2_checks, diffs = run_d2(cfg, seed)
    for dline in diffs:
        print(f"D2 transcription mismatch: {dline}")
    for c in d2_checks:
        if not c["ok"]:
            print(f"D2 gate red: {c['name']} observed={c['observed']} expected={c['expected']}")
    if not d1_out or not d2_out:
        print("Gates failed; no results written.")
        return 1

    metrics = clean({"seed": seed, "bootstrap": cfg["bootstrap"], "d1_gate_v1": d1_checks,
                     "d2_gate": d2_checks, "d1": d1_out, "d2": d2_out})
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                                      encoding="utf-8", newline="\n")
    write_report(out / "report.md", metrics)
    print(f"wrote {out / 'metrics.json'} and {out / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
