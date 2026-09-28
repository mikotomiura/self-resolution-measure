# self-resolution-measure

How far does an **outcome-agnostic** self-resolution measure drift from an **outcome-requiring** one when debugging episodes are closed by *either* a fix *or* the developer stopping? A reanalysis of two public, human-coded datasets of professional debugging.

| Measure | Definition |
|---|---|
| R0 | episodes that ended with no consultation of external resources / all episodes |
| R1 | resolved episodes that ended with no consultation / resolved episodes |
| R0′ | resolved episodes with no consultation / all episodes |
| numerator effect | R0 − R0′ = episodes that ended **unresolved and without consultation** / all episodes |
| denominator-only effect | R0′ − R1 (same numerator; denominator all → resolved) |
| conditioning effect | R0 − R1 = numerator effect + denominator-only effect |

## Data

- **D1** — Alaboudi & LaToza: 89 debugging episodes by 11 developers in live-streamed open-source work (arXiv:2105.02162v1; *Empirical Software Engineering* 28:117, 2023). The replication packages linked from the two versions carry the same coding (byte-identical `rowData.json`).
- **D2** — Li & Coblenz: 17 debugging tasks by 7 professional developers and 5 streamers (*Proc. ACM Softw. Eng.* 3(FSE):FSE049, 2026), from the paper's Table 4 and Table 5 only.

Both are CC BY 4.0. No raw data is committed; see [DATA.md](DATA.md) for sources, hashes and how to obtain them.

## Reproduce

```bash
# put either figshare zip for D1 into raw/ first (DATA.md, "How to obtain")
bash run.sh
```

`run.sh` checks input hashes, runs the self-test (the gates must turn red on absent or broken input, the consultation rules must match a truth table, and synthetic controls must recover known values), runs the analysis, runs it a second time under another hash seed and requires byte-identical output, requires the output to equal the bundled `results/` (compared with `cmp`, so it also works without git; set `ALLOW_RESULT_CHANGE=1` only after an intended change), and records hashes of every input and script in `results/provenance.txt`.

Outputs: `results/metrics.json`, `results/report.md`.

## Licence

- Code (`analysis/`, `run.sh`): Apache License 2.0 ([LICENSE](LICENSE)).
- Data derived here (`data/`, `results/`), `config.json` and documentation: CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)). Sentences quoted from third-party papers (in `config.json`, `results/` and `data/`) are quotations and remain under their original terms.
- Third-party sources keep their own licences and must be attributed: the Alaboudi & LaToza replication packages (CC BY 4.0; not redistributed here) and the Li & Coblenz paper (CC BY 4.0; its tables are transcribed in `data/li-coblenz-2026/`, see [data/li-coblenz-2026/README.md](data/li-coblenz-2026/README.md)).

## Layout

| Path | What |
|---|---|
| `config.json` | Analysis definitions, frozen before results were computed |
| `NOTES.md` | Question, what is not new, the freeze, deviations |
| `DATA.md` | Provenance of every input |
| `ENV.md` | Environment |
| `analysis/` | `d1.py` (episode extraction, gate, EMSE 2023 reproduction), `d2.py` (transcriptions, gate), `stats.py` (measures, Wilson, cluster bootstrap), `analyze.py` (entry point) |
| `data/li-coblenz-2026/` | Two independent (LLM-assisted) transcriptions of the Li & Coblenz tables, and three quoted sentences used in a sensitivity analysis |
