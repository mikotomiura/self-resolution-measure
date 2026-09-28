"""Write paper/results.tex from results/metrics.json. Standard library only.

Every number in the manuscript that comes from the analysis is taken from here as
\\R{<key>}; an unknown key stops the LaTeX run (see \\R in main.tex). Percentages are
formatted exactly as in results/report.md (one decimal, `f"{100 * x:.1f}"`), so the
paper and the report cannot disagree by rounding. Qualitative statements in the text
are checked in claims(); if the metrics no longer support one, nothing is written.

    python paper/make_results.py              # writes paper/results.tex
    python paper/make_results.py --stdout     # prints it (build.sh compares it with the file)
    python paper/make_results.py --selftest   # the checks must stop on falsified metrics
"""

from __future__ import annotations

import copy
import json
import re
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
GATE_ITEMS = {"episodes": "episodes", "debugging activities": "activities",
              "committed-defect episodes": "committed", "fresh-defect episodes": "fresh",
              "developers (EMSE 2023 Table 2)": "developers", "sessions (EMSE 2023 Table 2)": "sessions"}

# Keys go into \csname; values are either plain text or one of a few TeX fragments that
# this script produces itself. Anything else stops the run (no escaping guesswork).
KEY_RE = re.compile(r"[A-Za-z0-9/.-]+")
PLAIN_RE = re.compile(r"[A-Za-z0-9 ,./()+-]+")
# Plain values that would print wrongly: missing/non-finite numbers and a raw hyphen as minus.
BAD_PLAIN_RE = re.compile(r"(?i)\s*(none|null|nan|[+-]?inf(inity)?|n/a)\s*|-[0-9.].*")
TEX_RE = re.compile(r"(\\ensuremath\{-\})?[0-9]+(\.[0-9]+)?(\\%)?|\\rep(ok|no)|[0-9]+(\{,\}[0-9]{3})+")
END_CODES = ("DF2", "DF3", "DF5")   # outcome codes an unresolved episode can end with (DF4 is merged)


class ClaimError(SystemExit):
    pass


def signed(text: str) -> str:
    return "\\ensuremath{-}" + text[1:] if text.startswith("-") else text


def number(x, what: str = "value") -> float:
    if x is None or isinstance(x, bool) or not isinstance(x, (int, float)) or x != x or x in (float("inf"), float("-inf")):
        raise SystemExit(f"{what}: not a finite number: {x!r}")
    return x


def pct(x, digits: int = 1) -> str:
    return signed(f"{100 * number(x):.{digits}f}")


def shown(x) -> float:
    """The value as printed (one decimal, in percent); claims are judged on it."""
    return float(f"{100 * number(x):.1f}")


def ratio(k: int, n: int, what: str) -> float:
    if n <= 0:
        raise SystemExit(f"{what}: denominator is {n}")
    return k / n


def fail(msg: str) -> None:
    raise ClaimError("claim no longer holds: " + msg)


def build(m: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    def put(key: str, value) -> None:
        value = str(value)
        if not KEY_RE.fullmatch(key):
            raise SystemExit(f"key not allowed: {key!r}")
        plain_ok = PLAIN_RE.fullmatch(value) and not BAD_PLAIN_RE.fullmatch(value)
        if not (plain_ok or TEX_RE.fullmatch(value)):
            raise SystemExit(f"value not allowed for {key}: {value!r}")
        out.append((key, value))

    b = m["bootstrap"]
    put("boot/replicates", f"{b['replicates']:,}".replace(",", "{,}"))
    put("boot/level", f"{round(100 * b['level'])}")
    put("seed", m["seed"])

    for name, key in (("d1_gate_v1", "gate/d1"), ("d2_gate", "gate/d2")):
        checks = m[name]
        if not checks:
            raise SystemExit(f"{name}: no checks recorded")
        ok = sum(c["ok"] for c in checks)
        if ok != len(checks):
            raise SystemExit(f"{name}: {len(checks) - ok} red items; refusing to write the paper numbers")
        put(key + "/ok", ok)
        put(key + "/n", len(checks))
    observed = {c["name"]: c["observed"] for c in m["d1_gate_v1"]}
    for name, key in GATE_ITEMS.items():
        if name not in observed:
            raise SystemExit(f"d1_gate_v1: item {name!r} missing")
        put(f"d1/gate/{key}", f"{observed[name]:,}".replace(",", "{,}"))

    def unit_results(prefix: str, r: dict) -> None:
        c, p = r["counts"], r["point"]
        boot = r["cluster_bootstrap"]
        if any(v != 0 for v in boot["undefined_replicates"].values()):
            raise SystemExit(f"{prefix}: undefined bootstrap replicates {boot['undefined_replicates']}")
        n, res, free, a = c["n"], c["resolved"], c["no_consult"], c["resolved_no_consult"]
        bb = r["unresolved_no_consult"]
        unres = n - res
        if not (0 <= a <= res <= n and a <= free <= n and 0 <= bb <= unres):
            raise SystemExit(f"{prefix}: inconsistent counts {c} (unresolved_no_consult {bb})")
        if bb != free - a:
            raise SystemExit(f"{prefix}: unresolved_no_consult {bb} != {free} - {a}")
        for k, v in (("n", n), ("S", res), ("U", unres), ("free", free), ("a", a), ("b", bb),
                     ("cr", res - a), ("cu", unres - bb), ("cons", n - free), ("K", boot["clusters"])):
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
        put(f"{prefix}/Q", pct(ratio(bb, unres, prefix)))                # unconsulted among unresolved
        put(f"{prefix}/Ushare", pct(ratio(unres, n, prefix)))           # unresolved among all
        put(f"{prefix}/cuPct", pct(ratio(unres - bb, unres, prefix)))   # consulted among unresolved
        put(f"{prefix}/crPct", pct(ratio(res - a, res, prefix)))        # consulted among resolved
        put(f"{prefix}/p0", pct(r["p_replicate_without_numerator_units"]))
        by_code = r.get("unresolved_no_consult_by_code")
        if by_code is not None:
            if sum(by_code.values()) != bb:
                raise SystemExit(f"{prefix}: end-code breakdown {by_code} does not add up to {bb}")
            unexpected = sorted(set(by_code) - set(END_CODES))
            if unexpected:
                raise SystemExit(f"{prefix}: unexpected end codes {unexpected} (the text names DF2, DF3, DF5 only)")
            for code in END_CODES:
                put(f"{prefix}/bcode/{code}", by_code.get(code, 0))

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
            put(pre + "/crPct", pct(ratio(k1, n1, pre)))
            put(pre + "/cuPct", pct(ratio(k2, n2, pre)))
            put(pre + "/ne", pct(s["point"]["numerator_effect"]))
            put(pre + "/b", s["counts"]["no_consult"] - s["counts"]["resolved_no_consult"])
    rep = d1["reproduce_emse2023"]
    for mode, mkey in D1_MODES.items():
        rows = {r["item"]: r for r in rep[mode]["rows"]}
        if tuple(rows) != REPRO_ITEMS:
            raise SystemExit(f"reproduce_emse2023/{mode}: items {tuple(rows)} != {REPRO_ITEMS}")
        for item, r in rows.items():
            if item == "activities":
                obs = f"{r['observed']:,}".replace(",", "{,}")
            elif item == "time_share_top23":
                obs = pct(r["observed"]) + "\\%"
            else:
                obs = r["observed_text"]
            put(f"emse/{item.replace('_', '')}/{mkey}", obs)
            put(f"emse/{item.replace('_', '')}/{mkey}/ok", "\\repok" if r["match"] else "\\repno")
        put(f"emse/matched/{mkey}", f"{rep[mode]['matched']}/{rep[mode]['items']}")
    for r in rep["strict"]["rows"]:
        v = r["reported"]
        text = f"{v:,}".replace(",", "{,}") if r["item"] == "activities" else f"{round(100 * v)}\\%"
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
    """Qualitative statements made in the text, judged on the printed values where the
    text reads the printed values, and on integer counts where it reads counts."""
    d1 = dict(m["d1"]["results"])
    d2 = dict(m["d2"]["results"])
    cells = list(d1.values()) + list(d2.values())

    def point(r, key):
        return r["point"][key]

    def ivl(r, key):
        return r["cluster_bootstrap"]["intervals"][key]

    # Conditioning effect: printed point estimate negative and printed interval containing 0.
    if not all(shown(point(r, "conditioning_effect")) < 0 for r in cells):
        fail("every conditioning-effect point estimate is negative")
    if not all(shown(ivl(r, "conditioning_effect")[0]) <= 0 <= shown(ivl(r, "conditioning_effect")[1])
               for r in cells):
        fail("every conditioning-effect interval contains 0")
    ce = sorted(point(r, "conditioning_effect") for r in cells)
    put("all/ce/max", pct(ce[-1]))   # closest to zero
    put("all/ce/min", pct(ce[0]))    # furthest from zero
    put("all/cells", len(cells))
    # Denominator-only effect: printed interval entirely below 0.
    if not all(shown(ivl(r, "denominator_only_effect")[1]) < 0 for r in cells):
        fail("every denominator-only-effect interval lies below 0")
    # Numerator effect: D1 printed lower ends above 0; D2 lower ends print as 0.0.
    if not all(shown(ivl(r, "numerator_effect")[0]) > 0 for r in d1.values()):
        fail("every D1 numerator-effect interval lies above 0")
    if not all(number(ivl(r, "numerator_effect")[0]) == 0 for r in d2.values()):
        fail("every D2 numerator-effect interval starts at 0")
    if not all(number(r["p_replicate_without_numerator_units"]) > 0.025 for r in d2.values()):
        fail("in D2 the probability of a replicate without such tasks is above 2.5%")
    ne = sorted(point(r, "numerator_effect") for r in d1.values())
    put("d1/ne/min", pct(ne[0]))
    put("d1/ne/max", pct(ne[-1]))
    put("d1/cells", len(d1))
    # Under DF1, the fresh-defect component is the same under all four consultation rules
    # and equals the smallest DF1 numerator effect (committed contributes 0 there). Counts.
    st = m["d1"]["strata_by_origin"]
    n1 = d1["strict|DF1"]["counts"]["n"]
    for mode, s in st.items():
        if s["committed"]["counts"]["n"] + s["fresh"]["counts"]["n"] != n1:
            fail(f"strata {mode} partition the {n1} episodes")
    fresh_b = {mode: s["fresh"]["counts"]["no_consult"] - s["fresh"]["counts"]["resolved_no_consult"]
               for mode, s in st.items()}
    if len(set(fresh_b.values())) != 1:
        fail(f"fresh-defect unresolved-unconsulted count is the same under all rules: {fresh_b}")
    fb = next(iter(fresh_b.values()))
    if min(d1[f"{mode}|DF1"]["unresolved_no_consult"] for mode in st) != fb:
        fail("the smallest DF1 numerator effect equals the fresh-defect component")
    put("d1/freshb", fb)
    put("d1/freshshare", pct(fb / n1))
    # Most unresolved, unconsulted episodes (strict, DF1) end with DF3 ("return later").
    by_code = d1["strict|DF1"].get("unresolved_no_consult_by_code") or {}
    if not by_code or max(by_code, key=by_code.get) != "DF3" or 2 * by_code["DF3"] <= sum(by_code.values()):
        fail(f"most unresolved, unconsulted episodes end with DF3: {by_code}")
    # Pooled (strict, DF1): consultation more common among unresolved episodes; the committed
    # stratum reverses it; the fresh stratum keeps the pooled direction.
    s = st["strict"]
    k1, n1r = s["committed"]["consulted_among_resolved"]
    k2, n2u = s["committed"]["consulted_among_unresolved"]
    if not k1 * n2u > k2 * n1r:
        fail("committed (strict): consultation more common among resolved than unresolved")
    if not (n1r == n2u and k1 - k2 == 1):
        fail("committed (strict): the reversal is a difference of a single episode")
    # D2 table+text: the denominator-only effect outweighs the numerator effect (no cancelling).
    tt_point = m["d2"]["results"]["table5_plus_text"]["point"]
    if not abs(tt_point["denominator_only_effect"]) > 2 * abs(tt_point["numerator_effect"]):
        fail("D2 table+text: the numerator effect is much smaller than the denominator-only effect")
    f1, m1 = s["fresh"]["consulted_among_resolved"]
    f2, m2 = s["fresh"]["consulted_among_unresolved"]
    if not f2 * m1 > f1 * m2:
        fail("fresh (strict): consultation more common among unresolved than resolved")
    c = d1["strict|DF1"]["counts"]
    unres = c["n"] - c["resolved"]
    cu = unres - d1["strict|DF1"]["unresolved_no_consult"]
    cr = c["resolved"] - c["resolved_no_consult"]
    if not cu * c["resolved"] > cr * unres:
        fail("pooled (strict, DF1): consultation more common among unresolved than resolved")
    # Committed-defect episodes were both more often unresolved and more often consulted (strict).
    com, fre = s["committed"]["counts"], s["fresh"]["counts"]
    com_consulted = com["n"] - com["no_consult"]
    fre_consulted = fre["n"] - fre["no_consult"]
    if not (com["n"] - com["resolved"]) * fre["n"] > (fre["n"] - fre["resolved"]) * com["n"]:
        fail("committed episodes were more often unresolved than fresh ones")
    if not com_consulted * fre["n"] > fre_consulted * com["n"]:
        fail("committed episodes were more often consulted than fresh ones (strict)")
    put("d1/origin/committed/unres", f"{com['n'] - com['resolved']}/{com['n']}")
    put("d1/origin/fresh/unres", f"{fre['n'] - fre['resolved']}/{fre['n']}")
    put("d1/origin/committed/cons", f"{com_consulted}/{com['n']}")
    put("d1/origin/fresh/cons", f"{fre_consulted}/{fre['n']}")
    # EMSE 2023 reproduction, as stated in the text.
    rep = m["d1"]["reproduce_emse2023"]
    ok = {mode: {r["item"]: r["match"] for r in rep[mode]["rows"]} for mode in rep}
    with_it, without_it = ("ot2", "ot2u"), ("strict", "u")
    if any(rep[mode]["matched"] == rep[mode]["items"] for mode in rep):
        fail("no consultation rule reproduces every EMSE 2023 item")
    if len({rep[k]["matched"] for k in ("u", "ot2", "ot2u")}) != 1 or \
            not rep["strict"]["matched"] > rep["u"]["matched"]:
        fail("strict reproduces the most items; the three other rules tie")
    if not all(ok[mm]["time_share_top23"] and ok[mm]["short_with_consult"] for mm in ok):
        fail("the time share and the short-episode figure are reproduced under every rule")
    if not (all(ok[mm]["committed_with_consult"] for mm in with_it)
            and not any(ok[mm]["committed_with_consult"] for mm in without_it)):
        fail("'all committed consulted' is reproduced only with issue-tracker activities")
    for item in ("fresh_with_consult", "developers_with_consult"):
        if any(ok[mm][item] for mm in with_it) or not any(ok[mm][item] for mm in without_it):
            fail(f"{item} is reproduced only without issue-tracker activities")
    if any(ok[mm][item] for mm in ok for item in ("activities", "episodes_with_consult", "long_with_consult")):
        fail("activities, episodes consulted and long episodes consulted are reproduced under no rule")
    put("emse/items", next(iter(rep.values()))["items"])
    # D2: adding the text-described consultations halves the numerator effect (same n, b > 0),
    # and the unresolved, unconsulted tasks come from k developers, k from ((K - k)/K)^K.
    t5, tt = d2["table5"], d2["table5_plus_text"]
    b_table, b_text = t5["unresolved_no_consult"], tt["unresolved_no_consult"]
    if t5["counts"]["n"] != tt["counts"]["n"] or b_text <= 0 or b_table != 2 * b_text:
        fail(f"adding text-described consultations halves the D2 numerator effect ({b_table} -> {b_text})")
    for mode, key in (("table5", "table5"), ("table5_plus_text", "text")):
        r = d2[mode]
        big_k = r["cluster_bootstrap"]["clusters"]
        p0 = r["p_replicate_without_numerator_units"]
        fits = [k for k in range(1, r["unresolved_no_consult"] + 1)
                if abs(((big_k - k) / big_k) ** big_k - p0) <= 5e-7 + 1e-12]
        if len(fits) != 1:
            fail(f"D2 {mode}: p0 {p0} identifies one k in 1..b, got {fits}")
        put(f"d2/{key}/k", fits[0])


def render(pairs: list[tuple[str, str]]) -> str:
    lines = ["% Generated by paper/make_results.py from results/metrics.json. Do not edit.",
             "% build.sh regenerates this file and requires it to be identical."]
    for key, value in pairs:
        lines.append(f"\\expandafter\\def\\csname r@{key}\\endcsname{{{value}}}")
    return "\n".join(lines) + "\n"


def selftest(m: dict) -> int:
    """Each mutation must stop build(); the unmodified metrics must pass."""
    failures = []

    def expect_stop(name, mutate, reason):
        """The mutation must stop build() for the intended reason, not for another one."""
        mm = copy.deepcopy(m)
        mutate(mm)
        try:
            build(mm)
        except SystemExit as e:
            if reason in str(e):
                print(f"  [PASS] {name} -- stopped: {e}")
            else:
                print(f"  [FAIL] {name} -- stopped for another reason: {e}")
                failures.append(name)
            return
        print(f"  [FAIL] {name} -- not stopped")
        failures.append(name)

    def expect_pass(name, mutate):
        mm = copy.deepcopy(m)
        mutate(mm)
        try:
            build(mm)
            print(f"  [PASS] {name} -- passes")
        except SystemExit as e:
            print(f"  [FAIL] {name} -- stopped: {e}")
            failures.append(name)

    def res(mm, ds, key):
        return mm[ds]["results"][key]

    def setp(path, value):
        def f(mm):
            node = mm
            for p in path[:-1]:
                node = node[p]
            node[path[-1]] = value
        return f

    try:
        build(copy.deepcopy(m))
        print("  [PASS] unmodified metrics pass")
    except SystemExit as e:
        print(f"  [FAIL] unmodified metrics stopped: {e}")
        failures.append("unmodified")
    def ivl(mm, ds, key, measure):
        return res(mm, ds, key)["cluster_bootstrap"]["intervals"][measure]

    def strata(mm, origin):
        return mm["d1"]["strata_by_origin"]["strict"][origin]

    expect_pass("conditioning-effect interval with an upper end printing as 0.0",
                lambda mm: ivl(mm, "d1", "strict|DF1", "conditioning_effect").__setitem__(1, 0.0004))
    expect_stop("conditioning effect made positive",
                lambda mm: res(mm, "d2", "table5")["point"].__setitem__("conditioning_effect", 0.01),
                "point estimate is negative")
    expect_stop("conditioning-effect interval excluding 0",
                lambda mm: ivl(mm, "d1", "u|DF1", "conditioning_effect").__setitem__(1, -0.001),
                "interval contains 0")
    expect_stop("D1 numerator-effect lower end printing as 0.0",
                lambda mm: ivl(mm, "d1", "strict|DF1", "numerator_effect").__setitem__(0, 0.0004),
                "D1 numerator-effect interval lies above 0")
    expect_stop("denominator-only upper end printing as -0.0",
                lambda mm: ivl(mm, "d1", "u|DF1", "denominator_only_effect").__setitem__(1, -0.0003),
                "denominator-only-effect interval lies below 0")
    expect_stop("D2 numerator-effect lower end above 0",
                lambda mm: ivl(mm, "d2", "table5", "numerator_effect").__setitem__(0, 0.001),
                "D2 numerator-effect interval starts at 0")
    expect_stop("D2 table and table+text on different n",
                lambda mm: res(mm, "d2", "table5")["counts"].__setitem__("n", 30),
                "halves the D2 numerator effect")
    expect_stop("D2 p0 below 2.5%",
                lambda mm: res(mm, "d2", "table5").__setitem__("p_replicate_without_numerator_units", 0.0),
                "above 2.5%")
    expect_stop("D2 p0 not of the form ((K-k)/K)^K",
                lambda mm: res(mm, "d2", "table5").__setitem__("p_replicate_without_numerator_units", 0.2),
                "identifies one k")
    expect_stop("empty gate list", setp(["d2_gate"], []), "no checks recorded")
    expect_stop("value with a TeX special character",
                lambda mm: mm["d1"]["reproduce_emse2023"]["strict"]["rows"][2].__setitem__("observed_text", "19%89"),
                "value not allowed")
    expect_stop("value that would print a hyphen as a minus sign",
                lambda mm: mm["d1"]["reproduce_emse2023"]["strict"]["rows"][2].__setitem__("observed_text", "-3.4"),
                "value not allowed")
    expect_stop("inconsistent counts (more resolved-unconsulted than resolved)",
                lambda mm: res(mm, "d2", "table5_plus_text")["counts"].__setitem__("resolved", 0),
                "inconsistent counts")
    expect_stop("zero resolved units (a share would be undefined)",
                lambda mm: res(mm, "d2", "table5_plus_text").__setitem__(
                    "counts", {"n": 17, "resolved": 0, "no_consult": 1, "resolved_no_consult": 0}),
                "denominator is 0")
    expect_stop("undefined point estimate (null in metrics.json)",
                lambda mm: res(mm, "d2", "table5_plus_text")["point"].__setitem__("R1", None),
                "not a finite number")
    expect_stop("end-code breakdown not adding up",
                lambda mm: res(mm, "d1", "strict|DF1")["unresolved_no_consult_by_code"].__setitem__("DF3", 7),
                "does not add up")
    expect_stop("unexpected end code",
                lambda mm: res(mm, "d1", "strict|DF1").__setitem__(
                    "unresolved_no_consult_by_code", {"DF2": 1, "DF3": 8, "none": 1}),
                "unexpected end codes")
    expect_stop("DF3 no longer the majority",
                lambda mm: res(mm, "d1", "strict|DF1").__setitem__(
                    "unresolved_no_consult_by_code", {"DF2": 5, "DF3": 4, "DF5": 1}),
                "most unresolved, unconsulted episodes end with DF3")
    expect_stop("committed reversal larger than one episode",
                lambda mm: strata(mm, "committed").__setitem__("consulted_among_unresolved", [2, 5]),
                "difference of a single episode")
    expect_stop("fresh stratum reversing the pooled direction",
                lambda mm: strata(mm, "fresh").__setitem__("consulted_among_unresolved", [1, 11]),
                "fresh (strict)")
    expect_stop("D2 table+text effects no longer far apart",
                lambda mm: res(mm, "d2", "table5_plus_text")["point"].__setitem__("denominator_only_effect", -0.08),
                "much smaller than the denominator-only effect")
    expect_stop("committed figure reproduced without issue-tracker activities",
                lambda mm: mm["d1"]["reproduce_emse2023"]["strict"]["rows"][3].__setitem__("match", True),
                "only with issue-tracker activities")
    print(f"make_results selftest: {'OK' if not failures else str(len(failures)) + ' FAILED'}")
    return 1 if failures else 0


def main() -> int:
    m = json.loads(METRICS.read_text(encoding="utf-8"))
    if "--selftest" in sys.argv[1:]:
        return selftest(m)
    text = render(build(m))
    if "--stdout" in sys.argv[1:]:
        sys.stdout.buffer.write(text.encode("utf-8"))
    else:
        OUT.write_bytes(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
