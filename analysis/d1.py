"""D1: Alaboudi & LaToza live-streamed debugging episodes (public `rowData.json`).

Episode extraction follows the codebook shipped in both replication packages:

  DF4 "No, the developer got interrupted during the episode."   (how a block ends)
  DF7 "The developer returns from other activity."               (how a block starts)

A block that starts with DF7 continues the most recent episode that ended with DF4 in
the same session. Without this, the 109 debugging blocks do not reduce to the 89
episodes reported by both versions of the paper.
"""

from __future__ import annotations

import re
import statistics

from stats import Unit

DF_CODE = re.compile(r"DF(\d+)")
U_CODE = re.compile(r"\bU\d+\b")
OT_CODE = re.compile(r"\bOT(\d+)\b")

SEEKING = "Seeking information"
OTHERS = "Others"
DF_FIX_YES, DF_FIX_MOSTLY = 1, 2
DF_OUTCOME = {1, 2, 3, 4, 5}
DF_INTERRUPTED = 4
DF_RESUME = 7
DF_REPORTED = 8          # "The developer received a bug report and started reproducing the defect."
OT_ISSUE_TRACKER = "2"   # OT2: Issue tracker

CONSULT_MODES = ("strict", "u", "ot2", "ot2u")


def hhmmss(text: str) -> int:
    parts = [int(x) for x in text.strip().split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts[-3], parts[-2], parts[-1]
    return h * 3600 + m * 60 + s


def span(node: dict) -> tuple[int, int]:
    d = node["duration"]
    return hhmmss(d["start"]["time"]), hhmmss(d["end"]["time"])


def build_episodes(sessions: list, diag: dict | None = None, merge: bool = True) -> list[dict]:
    if diag is None:
        diag = {}
    for key in ("max_open_episodes", "orphan_resumes", "unresumed_interruptions",
                "temporal_violations", "same_start_debugging_blocks"):
        diag.setdefault(key, 0)

    episodes: list[dict] = []
    for sess in sessions:
        # The array order is not chronological in 6 of the 15 sessions. Ties on the
        # start time are broken by the end time so that the order never depends on
        # the array order; the number of such ties is reported.
        anns = sorted(sess["annotations"], key=lambda a: span(a))
        starts = [span(a)[0] for a in anns if a["title"] == "Debugging"]
        diag["same_start_debugging_blocks"] += len(starts) - len(set(starts))
        pending: list[dict] = []
        for ann in anns:
            if ann["title"] != "Debugging":
                continue
            codes = {int(x) for x in DF_CODE.findall(ann.get("description", ""))}
            start, end = span(ann)
            block = {"codes": codes, "start": start, "end": end,
                     "subs": ann.get("subAnnotations") or []}
            if merge and DF_RESUME in codes and pending:
                episode = pending.pop()
                if episode["blocks"][-1]["end"] > block["start"]:
                    diag["temporal_violations"] += 1
                episode["blocks"].append(block)
            else:
                if merge and DF_RESUME in codes:
                    diag["orphan_resumes"] += 1
                episode = {"session": sess["id"], "cluster": sess["githubURL"], "blocks": [block]}
                episodes.append(episode)
            if merge and DF_INTERRUPTED in codes:
                pending.append(episode)
                diag["max_open_episodes"] = max(diag["max_open_episodes"], len(pending))
        diag["unresumed_interruptions"] += len(pending)
    return episodes


def first_codes(ep: dict) -> set:
    return ep["blocks"][0]["codes"]


def last_codes(ep: dict) -> set:
    return ep["blocks"][-1]["codes"]


def is_resolved(ep: dict, codes: tuple[str, ...] = ("DF1",)) -> bool:
    wanted = {int(c[2:]) for c in codes}
    return bool(last_codes(ep) & wanted)


def is_committed(ep: dict) -> bool:
    return DF_REPORTED in first_codes(ep)


def is_consult(sub: dict, mode: str) -> bool:
    title = sub.get("title", "")
    if title == SEEKING:
        return True
    if title != OTHERS or mode == "strict":
        return False
    desc = sub.get("description", "")
    has_u = bool(U_CODE.search(desc))
    has_ot2 = OT_ISSUE_TRACKER in OT_CODE.findall(desc)
    return {"u": has_u, "ot2": has_ot2, "ot2u": has_u or has_ot2}[mode]


def consult_subs(ep: dict, mode: str = "strict") -> list[dict]:
    return [s for b in ep["blocks"] for s in b["subs"] if is_consult(s, mode)]


def episode_seconds(ep: dict) -> int:
    return sum(b["end"] - b["start"] for b in ep["blocks"])


LOOSE_CODE = re.compile(r"(?<![A-Za-z])(?:OT|U)\s*-?\s*\d+")
STRICT_CODE = re.compile(r"\b(?:OT|U)\d+\b")


def code_token_misses(sessions: list) -> int:
    """Sub-annotations whose OT/U-like tokens are not all matched by the strict patterns
    used in `is_consult` (e.g. "OT-2", "OT 2", "OT2U1"). Must be 0, or the consultation
    definitions silently miss codes."""
    misses = 0
    for sess in sessions:
        for ann in sess["annotations"]:
            for sub in ann.get("subAnnotations") or []:
                desc = sub.get("description", "")
                if len(LOOSE_CODE.findall(desc)) != len(STRICT_CODE.findall(desc)):
                    misses += 1
    return misses


def to_units(episodes: list[dict], mode: str, resolved_codes: tuple[str, ...]) -> list[Unit]:
    return [Unit(cluster=ep["cluster"], resolved=is_resolved(ep, resolved_codes),
                 consulted=bool(consult_subs(ep, mode))) for ep in episodes]


# ---------------------------------------------------------------------------
# Gate: the extraction must reproduce the arXiv v1 figures
# ---------------------------------------------------------------------------
def _chk(name: str, observed, expected, tol) -> dict:
    ok = abs(float(observed) - float(expected)) <= tol
    return {"name": name, "observed": observed, "expected": expected, "tolerance": tol, "ok": ok}


def _val(spec) -> tuple[float, float]:
    if isinstance(spec, dict):
        return spec["value"], spec.get("tolerance", 0)
    return spec, 0


def gate_v1(episodes: list[dict], diag: dict, g: dict, sessions: list | None = None) -> list[dict]:
    n_act = sum(len(b["subs"]) for ep in episodes for b in ep["blocks"])
    per_ep = [sum(len(b["subs"]) for b in ep["blocks"]) for ep in episodes]
    committed = [ep for ep in episodes if is_committed(ep)]
    fresh = [ep for ep in episodes if not is_committed(ep)]

    counts, fracs, secs = [], [], []
    for ep in episodes:
        acts = consult_subs(ep, "strict")
        total = episode_seconds(ep)
        s = 0
        for a in acts:
            a0, a1 = span(a)
            s += a1 - a0
            secs.append(a1 - a0)
        counts.append(len(acts))
        fracs.append(s / total if total > 0 else 0.0)

    lo, hi = g["consult_count_range"]
    checks = [
        _chk("episodes", len(episodes), *_val(g["episodes"])),
        _chk("debugging activities", n_act, *_val(g["debug_activities"])),
        _chk("activities per episode (mean)", statistics.mean(per_ep), *_val(g["activities_per_episode_avg"])),
        _chk("committed-defect episodes", len(committed), *_val(g["origin_committed"])),
        _chk("fresh-defect episodes", len(fresh), *_val(g["origin_fresh"])),
        _chk("unresolved rate, committed", sum(not is_resolved(e) for e in committed) / len(committed),
             *_val(g["unresolved_rate_committed"])),
        _chk("unresolved rate, fresh", sum(not is_resolved(e) for e in fresh) / len(fresh),
             *_val(g["unresolved_rate_fresh"])),
        _chk("consultations per episode (min)", min(counts), lo, 0),
        _chk("consultations per episode (max)", max(counts), hi, 0),
        _chk("consultation share of episode time (mean)", statistics.mean(fracs),
             *_val(g["consult_time_share_mean"])),
        _chk("consultation share of episode time (max)", max(fracs), *_val(g["consult_time_share_max"])),
        _chk("seconds per consultation (mean)", statistics.mean(secs) if secs else float("nan"),
             *_val(g["consult_seconds_per_instance_mean"])),
    ]
    for key, want in g["merge_invariants"].items():
        checks.append(_chk("merge invariant: " + key, diag.get(key, -1), want, 0))
    # Structural checks added after review (NOTES.md, Deviations): the EMSE 2023 paper's
    # Table 2 lists 15 videos by 11 developers; code tokens must all be recognised.
    checks.append(_chk("developers (EMSE 2023 Table 2)", len({e["cluster"] for e in episodes}), 11, 0))
    if sessions is not None:
        checks.append(_chk("sessions (EMSE 2023 Table 2)", len(sessions), 15, 0))
        checks.append(_chk("OT/U-like tokens not matched by the code patterns",
                           code_token_misses(sessions), 0, 0))
    return checks


# ---------------------------------------------------------------------------
# Not a gate: how far can the EMSE 2023 figures be reproduced from the same data?
# ---------------------------------------------------------------------------
def reproduce_emse(episodes: list[dict], spec: dict, short_n: int, long_n: int) -> dict:
    tol = spec["rounding_tolerance"]
    by_len = sorted(episodes, key=episode_seconds)
    short, long_ = by_len[:short_n], by_len[-long_n:]
    committed = [e for e in episodes if is_committed(e)]
    fresh = [e for e in episodes if not is_committed(e)]
    total = sum(episode_seconds(e) for e in episodes)
    n_act = sum(len(b["subs"]) for ep in episodes for b in ep["blocks"])

    def row(rows, key, observed, text):
        want = spec[key]["value"]
        exact = spec[key]["kind"] == "count"
        ok = observed == want if exact else abs(observed - want) <= tol
        rows.append({"item": key, "reported": want, "observed": observed, "observed_text": text,
                     "match": ok, "quote": spec[key].get("quote", "")})

    by_mode = {}
    for mode in CONSULT_MODES:
        rows: list[dict] = []
        row(rows, "activities", n_act, str(n_act))
        top_share = sum(episode_seconds(e) for e in long_) / total
        row(rows, "time_share_top23", top_share, f"{top_share:.4f}")
        has = {id(e): bool(consult_subs(e, mode)) for e in episodes}

        for key, group in (("episodes_with_consult", episodes), ("committed_with_consult", committed),
                           ("fresh_with_consult", fresh), ("short_with_consult", short),
                           ("long_with_consult", long_)):
            k = sum(has[id(e)] for e in group)
            row(rows, key, k / len(group), f"{k}/{len(group)}")
        devs: dict[str, bool] = {}
        for e in episodes:
            devs[e["cluster"]] = devs.get(e["cluster"], False) or has[id(e)]
        k = sum(devs.values())
        row(rows, "developers_with_consult", k / len(devs), f"{k}/{len(devs)}")
        by_mode[mode] = {"rows": rows, "matched": sum(r["match"] for r in rows), "items": len(rows)}
    return by_mode


def strata(episodes: list[dict], mode: str, resolved_codes: tuple[str, ...]) -> dict:
    from stats import counts, measures_from_counts
    out = {}
    for name, pred in (("committed", is_committed), ("fresh", lambda e: not is_committed(e))):
        group = [e for e in episodes if pred(e)]
        units = to_units(group, mode, resolved_codes)
        c = counts(units)
        consulted_resolved = sum(u.resolved and u.consulted for u in units)
        consulted_unresolved = sum((not u.resolved) and u.consulted for u in units)
        out[name] = {
            "counts": c,
            "consulted_among_resolved": [consulted_resolved, c["resolved"]],
            "consulted_among_unresolved": [consulted_unresolved, c["n"] - c["resolved"]],
            "point": measures_from_counts(c),
        }
    return out
