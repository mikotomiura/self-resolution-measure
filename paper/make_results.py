"""Write paper/results.tex from results/metrics.json. Standard library only.

Every number in the manuscript that comes from the analysis is taken from here as
\\R{<key>}; an unknown key stops the LaTeX run (see \\R in main.tex). Percentages are
formatted exactly as in results/report.md (one decimal, `f"{100 * x:.1f}"`), so the
paper and the report cannot disagree by rounding.

    python paper/make_results.py            # writes paper/results.tex
    python paper/make_results.py --stdout   # prints it (used by build.sh to compare)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "results" / "metrics.json"
OUT = ROOT / "paper" / "results.tex"

D1_MODES = {"strict": "strict", "u": "u", "ot2": "ot2", "ot2u": "ot2u"}
D1_RES = {"DF1": "DF1", "DF1+DF2": "DF12"}
D2_MODES = {"table5": "table5", "table5_plus_text": "text"}
MEASURE_KEYS = {"R0": "R0", "R1": "R1", "R0_prime": "R0p", "numerator_effect": "ne",
                "denominator_only_effect": "de", "conditioning_effect": "ce"}
REPRO_ITEMS = ("activities", "time_share_top23", "episodes_with_consult", "committed_with_consult",
               "fresh_with_consult", "short_with_consult", "long_with_consult", "developers_with_consult")


def signed(text: str) -> str:
    return "\\ensuremath{-}" + text[1:] if text.startswith("-") else text


def pct(x: float, digits: int = 1) -> str:
    return signed(f"{100 * x:.{digits}f}")


def build(m: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    def put(key: str, value) -> None:
        if any(ch in key for ch in "\\{}#%$&_^~ +|"):
            raise ValueError(f"key not safe for \\csname: {key!r}")
        out.append((key, str(value)))

    b = m["bootstrap"]
    put("boot/replicates", f"{b['replicates']:,}".replace(",", "{,}"))
    put("boot/level", f"{round(100 * b['level'])}")
    put("seed", m["seed"])

    for name, key in (("d1_gate_v1", "gate/d1"), ("d2_gate", "gate/d2")):
        checks = m[name]
        ok = sum(c["ok"] for c in checks)
        if ok != len(checks):
            raise SystemExit(f"{name}: {len(checks) - ok} red items; refusing to write the paper numbers")
        put(key + "/ok", ok)
        put(key + "/n", len(checks))

    def unit_results(prefix: str, r: dict) -> None:
        c, p = r["counts"], r["point"]
        boot = r["cluster_bootstrap"]
        if any(v != 0 for v in boot["undefined_replicates"].values()):
            raise SystemExit(f"{prefix}: undefined bootstrap replicates {boot['undefined_replicates']}")
        n, res, free, a = c["n"], c["resolved"], c["no_consult"], c["resolved_no_consult"]
        bb = r["unresolved_no_consult"]
        unres = n - res
        if bb != free - a:
            raise SystemExit(f"{prefix}: unresolved_no_consult {bb} != {free} - {a}")
        for k, v in (("n", n), ("S", res), ("U", unres), ("free", free), ("a", a), ("b", bb),
                     ("cr", res - a), ("cu", unres - bb), ("K", boot["clusters"])):
            put(f"{prefix}/{k}", v)
        for mk, short in MEASURE_KEYS.items():
            put(f"{prefix}/{short}", pct(p[mk]))
            put(f"{prefix}/{short}2", pct(p[mk], 2))
            lo, hi = boot["intervals"][mk]
            put(f"{prefix}/{short}/lo", pct(lo))
            put(f"{prefix}/{short}/hi", pct(hi))
        for mk, pair in r["wilson95"].items():
            put(f"{prefix}/{MEASURE_KEYS[mk]}/wlo", pct(pair[0]))
            put(f"{prefix}/{MEASURE_KEYS[mk]}/whi", pct(pair[1]))
        # Derived shares used in the text (computed here, never by hand).
        put(f"{prefix}/Q", pct(bb / unres) if unres else "n/a")          # unconsulted among unresolved
        put(f"{prefix}/Ushare", pct(unres / n))                          # unresolved among all
        put(f"{prefix}/cuPct", pct((unres - bb) / unres) if unres else "n/a")  # consulted among unresolved
        put(f"{prefix}/crPct", pct((res - a) / res) if res else "n/a")         # consulted among resolved
        put(f"{prefix}/p0", pct(r["p_replicate_without_numerator_units"]))

    d1 = m["d1"]
    put("d1/developers", d1["developers"])
    for mode, mkey in D1_MODES.items():
        for res, rkey in D1_RES.items():
            unit_results(f"d1/{mkey}/{rkey}", d1["results"][f"{mode}|{res}"])
    for code, v in d1["outcome_codes"].items():
        put(f"d1/codes/{code}", v)
    for mode, mkey in D1_MODES.items():
        for origin, s in d1["strata_by_origin"][mode].items():
            pre = f"d1/{mkey}/origin/{origin}"
            k1, n1 = s["consulted_among_resolved"]
            k2, n2 = s["consulted_among_unresolved"]
            put(pre + "/n", s["counts"]["n"])
            put(pre + "/cr", f"{k1}/{n1}")
            put(pre + "/cu", f"{k2}/{n2}")
            put(pre + "/ne", pct(s["point"]["numerator_effect"]))
            put(pre + "/b", s["counts"]["no_consult"] - s["counts"]["resolved_no_consult"])
    rep = d1["reproduce_emse2023"]
    for mode, mkey in D1_MODES.items():
        rows = {r["item"]: r for r in rep[mode]["rows"]}
        if tuple(rows) != REPRO_ITEMS:
            raise SystemExit(f"reproduce_emse2023/{mode}: items {tuple(rows)} != {REPRO_ITEMS}")
        for item, r in rows.items():
            if item == "activities":
                obs = r["observed_text"]
            elif item == "time_share_top23":
                obs = pct(r["observed"]) + "\\%"
            else:
                obs = r["observed_text"]
            put(f"emse/{item.replace('_', '')}/{mkey}", obs)
            put(f"emse/{item.replace('_', '')}/{mkey}/ok", "\\repok" if r["match"] else "\\repno")
        put(f"emse/matched/{mkey}", f"{rep[mode]['matched']}/{rep[mode]['items']}")
    for r in rep["strict"]["rows"]:
        v = r["reported"]
        text = str(v) if r["item"] == "activities" else f"{round(100 * v)}\\%"
        put(f"emse/{r['item'].replace('_', '')}/reported", text)

    d2 = m["d2"]
    put("d2/developers", d2["developers"])
    for mode, mkey in D2_MODES.items():
        unit_results(f"d2/{mkey}", d2["results"][mode])
    put("d2/texttasks", ", ".join(d2["text_described_tasks"]))
    ro = d2["report_only"]
    put("d2/streamermin", ro["streamer_minutes_table4"])
    put("d2/streamerhours", f"{ro['streamer_minutes_table4'] / 60:.2f}")
    put("d2/streamerhoursstated", ro["streamer_hours_stated"])

    claims(m, put)

    keys = [k for k, _ in out]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate keys")
    return out


def claims(m: dict, put) -> None:
    """Qualitative statements made in the text. Each is checked here, so a change in
    results/metrics.json that would make the prose false stops the build."""
    d1 = {k: v for k, v in m["d1"]["results"].items()}
    d2 = {k: v for k, v in m["d2"]["results"].items()}
    cells = list(d1.values()) + list(d2.values())

    def fail(msg: str) -> None:
        raise SystemExit("claim no longer holds: " + msg)

    def point(r, key):
        return r["point"][key]

    def ivl(r, key):
        return r["cluster_bootstrap"]["intervals"][key]

    # Conditioning effect: negative point estimate and an interval that contains 0, in all cells.
    if not all(point(r, "conditioning_effect") < 0 for r in cells):
        fail("every conditioning-effect point estimate is negative")
    if not all(ivl(r, "conditioning_effect")[0] <= 0 <= ivl(r, "conditioning_effect")[1] for r in cells):
        fail("every conditioning-effect interval contains 0")
    ce = sorted(point(r, "conditioning_effect") for r in cells)
    put("all/ce/max", pct(ce[-1]))   # closest to zero
    put("all/ce/min", pct(ce[0]))    # furthest from zero
    put("all/cells", len(cells))
    # Denominator-only effect: interval entirely below 0 in all cells.
    if not all(ivl(r, "denominator_only_effect")[1] < 0 for r in cells):
        fail("every denominator-only-effect interval lies below 0")
    # Numerator effect: D1 intervals exclude 0; D2 intervals start at 0.
    if not all(ivl(r, "numerator_effect")[0] > 0 for r in d1.values()):
        fail("every D1 numerator-effect interval lies above 0")
    if not all(abs(ivl(r, "numerator_effect")[0]) < 5e-4 for r in d2.values()):
        fail("every D2 numerator-effect interval starts at 0")
    ne = sorted(point(r, "numerator_effect") for r in d1.values())
    put("d1/ne/min", pct(ne[0]))
    put("d1/ne/max", pct(ne[-1]))
    put("d1/cells", len(d1))
    # Under DF1, the fresh-defect component is the same under all four consultation rules,
    # and it equals the smallest DF1 numerator effect (committed contributes 0 there).
    st = m["d1"]["strata_by_origin"]
    fresh_b = {mode: s["fresh"]["counts"]["no_consult"] - s["fresh"]["counts"]["resolved_no_consult"]
               for mode, s in st.items()}
    if len(set(fresh_b.values())) != 1:
        fail(f"fresh-defect unresolved-unconsulted count is the same under all rules: {fresh_b}")
    fb = next(iter(fresh_b.values()))
    n1 = d1["strict|DF1"]["counts"]["n"]
    put("d1/freshb", fb)
    put("d1/freshshare", pct(fb / n1))
    df1_min = min(point(d1[f"{mode}|DF1"], "numerator_effect") for mode in st)
    if abs(df1_min - fb / n1) > 5e-7:
        fail("the smallest DF1 numerator effect equals the fresh-defect component")
    # Pooled D1 (strict, DF1): consultation is more common among unresolved episodes,
    # but not among committed-defect episodes.
    s = st["strict"]
    k1, n1r = s["committed"]["consulted_among_resolved"]
    k2, n2u = s["committed"]["consulted_among_unresolved"]
    if not k1 / n1r > k2 / n2u:
        fail("committed (strict): consultation more common among resolved than unresolved")
    c = d1["strict|DF1"]["counts"]
    cr = (c["resolved"] - c["resolved_no_consult"]) / c["resolved"]
    cu = (c["n"] - c["resolved"] - d1["strict|DF1"]["unresolved_no_consult"]) / (c["n"] - c["resolved"])
    if not cu > cr:
        fail("pooled (strict, DF1): consultation more common among unresolved than resolved")
    # Committed-defect episodes were both more often unresolved and more often consulted (strict).
    com, fre = s["committed"]["counts"], s["fresh"]["counts"]
    com_consulted = com["n"] - com["no_consult"]
    fre_consulted = fre["n"] - fre["no_consult"]
    if not (com["n"] - com["resolved"]) / com["n"] > (fre["n"] - fre["resolved"]) / fre["n"]:
        fail("committed episodes were more often unresolved than fresh ones")
    if not com_consulted / com["n"] > fre_consulted / fre["n"]:
        fail("committed episodes were more often consulted than fresh ones (strict)")
    put("d1/origin/committed/unres", f"{com['n'] - com['resolved']}/{com['n']}")
    put("d1/origin/fresh/unres", f"{fre['n'] - fre['resolved']}/{fre['n']}")
    put("d1/origin/committed/cons", f"{com_consulted}/{com['n']}")
    put("d1/origin/fresh/cons", f"{fre_consulted}/{fre['n']}")
    # EMSE 2023 reproduction: no rule reproduces every item; the three non-strict rules tie.
    rep = m["d1"]["reproduce_emse2023"]
    if any(r["matched"] == r["items"] for r in rep.values()):
        fail("no consultation rule reproduces every EMSE 2023 item")
    if len({rep[k]["matched"] for k in ("u", "ot2", "ot2u")}) != 1:
        fail("the three non-strict rules reproduce the same number of EMSE 2023 items")
    put("emse/items", next(iter(rep.values()))["items"])
    # D2: adding the text-described consultations halves the numerator effect (2/17 -> 1/17),
    # and the unresolved, unconsulted tasks come from k developers (k from ((K-k)/K)^K).
    b_table = d2["table5"]["unresolved_no_consult"]
    b_text = d2["table5_plus_text"]["unresolved_no_consult"]
    if b_table != 2 * b_text:
        fail(f"adding text-described consultations halves the D2 numerator effect ({b_table} -> {b_text})")
    for mode, key in (("table5", "table5"), ("table5_plus_text", "text")):
        r = d2[mode]
        big_k = r["cluster_bootstrap"]["clusters"]
        p0 = r["p_replicate_without_numerator_units"]
        k = round(big_k - big_k * p0 ** (1 / big_k))
        if abs(((big_k - k) / big_k) ** big_k - p0) > 5e-6:
            fail(f"D2 {mode}: p0 {p0} is not ((K-k)/K)^K for an integer k")
        put(f"d2/{key}/k", k)


def render(pairs: list[tuple[str, str]]) -> str:
    lines = ["% Generated by paper/make_results.py from results/metrics.json. Do not edit.",
             "% build.sh regenerates this file and requires it to be identical."]
    for key, value in pairs:
        lines.append(f"\\expandafter\\def\\csname r@{key}\\endcsname{{{value}}}")
    return "\n".join(lines) + "\n"


def main() -> int:
    text = render(build(json.loads(METRICS.read_text(encoding="utf-8"))))
    if "--stdout" in sys.argv[1:]:
        sys.stdout.buffer.write(text.encode("utf-8"))
    else:
        OUT.write_bytes(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
