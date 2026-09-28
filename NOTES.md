# Notes

Exploratory reanalysis. No preregistration. Definitions were frozen in `config.json` before the main results were computed (see *Freeze*).

## Question

When a debugging episode is closed by *either* a fix *or* the developer stopping, how far does an outcome-agnostic self-resolution measure (R0: episodes with no consultation of external resources / all episodes) drift from an outcome-requiring one (R0′: resolved *and* no consultation / all episodes)? The difference R0 − R0′ is exactly the share of episodes that ended unresolved without any consultation.

- Both datasets close episodes with a fix or a stop. D1 (arXiv v1): "fixes the defect or decides to stop"; EMSE 2023: "until when the defect is fixed or the developer stops". D2 (streamers): "either the streamer's announcement that they gave up or had to continue another time, or the issue … fixed".
- In D2, an unresolved *participant* task (P4TA) was one not resolved "within the study period". There, "unresolved" includes administrative truncation, not only giving up.

## What is not new

- R0 itself was reported by the original authors as its complement (arXiv v1: consultation in 21% of episodes; EMSE 2023: 33%).
- The origin difference (committed vs fresh defects) in consultation was reported by the EMSE 2023 version.

## Freeze

- 2026-09-06: D1 extraction and the `strict` consultation mapping were fixed and checked against 12 figures of arXiv v1 (all passed; activities 2136 vs 2137 accepted with tolerance 1, cause unknown).
- 2026-09-28: the EMSE 2023 package was downloaded and found byte-identical to v1 for `rowData.json`. While identifying which rule could produce the EMSE figures, R0 / R0′ for the `ot2` and `ot2u` definitions were computed once in a scratch script (numerator effect about 0.09 vs 0.112 for `strict`). The primary definition was not changed after seeing them; all four definitions are reported.
- D2 values under `table5` (R0 = 11/17, R0′ = 9/17) were computed manually (outside this code) on 2026-09-28 before this repository existed. The body-text discrepancy (S5TA, P1TA) was noticed on the same day and its effect was worked out by hand once (numerator effect about 1/17) before the rule and its three quotes were fixed in `data/p434/text_external.csv` (now `data/li-coblenz-2026/`). The primary definition (`table5`) was set on 2026-09-28 before that and was not changed.
- `config.json` was committed before the analysis code produced `results/`.

## D2 transcription

- Both transcriptions were produced with an LLM-based assistant (Anthropic Claude): A by the session that ran the analysis, B by a separate instance given only the PDF, without access to A. They are byte-identical. Agreement between two instances of the same model guards against slips, not against a shared misreading; the totals check (`config.json` → `d2.gate`) is the independent safeguard. See `data/li-coblenz-2026/README.md`.
- For the body-text sensitivity, instance B independently listed the same two tasks that Table 5 omits (P1TA: colleagues and reports of similar issues; S5TA: brainstorming with stream viewers). B also found a documentation mention for "S4" that cannot be attributed to S4TA or S4TB; Table 5 lists S4TB. It is not added. S4TA is resolved, so adding it would lower R0 and R0′ by the same 1/17 and leave the numerator effect unchanged.

## Limitations of the intervals

With 11 (D1) or 12 (D2) developers, percentile cluster-bootstrap intervals are known to cover less than the nominal level. They are reported as frozen and should be read as a lower bound on uncertainty. `results/report.md` gives, for every row, the share ((K − k)/K)^K of replicates that draw none of the k developers with an unresolved, unconsulted unit; when it exceeds 2.5% the numerator-effect interval starts at 0 (D2: about 11% under `table5`, where k = 2, and about 35% under `table5_plus_text`, where k = 1).

## Deviations

Logged after the 2026-09-28 cross-review (Claude and Codex reviewers). No definition that produced a reported value was changed; all earlier values are unchanged in `results/`.

1. **Measure names.** `config.json` froze `denominator_effect = R0 − R1`. The review pointed out that R0 − R1 changes the numerator and the denominator at once. It is now reported as `conditioning_effect` (same value), and `denominator_only_effect = R0′ − R1` was added, so that R0 − R1 = (R0 − R0′) + (R0′ − R1). Pre-change text: `"denominator_effect": "R0 - R1"`.
2. **Data path.** `data/p434/` was renamed to `data/li-coblenz-2026/` (the old name matched a citation key in the author's other project). Pre-change paths: `data/p434/transcription_a.csv`, `data/p434/transcription_b.csv`, `data/p434/text_external.csv`.
3. **Added checks** (stricter gates, no change to any value): 11 developers and 15 sessions (EMSE 2023 Table 2); OT/U-like tokens not matched by the code patterns must be 0 (it is 0; the check is case-insensitive); value domains and `in_table5` agreement for D2; a truth table for the four consultation rules; the bootstrap must resample whole clusters; `check_config` compares the config with the constants the code actually uses (top-level title, cluster keys, D2 resolved value, interval method, measure names, consultation modes, resolved sets); the input hash is checked inside `analyze.py` as well as in `run.sh`; `run.sh` compares a fresh run with the bundled `results/` using `cmp` (no git needed) before replacing them.
4. **Tie-breaking.** Annotations are sorted by (start, end) instead of start only. The number of debugging blocks sharing a start time is reported (it is 0, so no result changed).
5. **Undefined bootstrap replicates.** A replicate where one measure is undefined (e.g. R1 with no resolved unit) is now dropped for that measure only, not for all measures. No replicate was undefined in any reported cell, so no interval changed.
6. **R1 wording.** The frozen text read `"R1": "episodes ending with zero consultations / resolved episodes"`, which could be read as all unconsulted episodes over resolved ones. The code has computed resolved-and-unconsulted over resolved since the first results (commit `834f16a`); the text now says so. No value changed.
