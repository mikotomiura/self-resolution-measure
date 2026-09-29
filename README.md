<div align="center">

# When "no help" is not "solved"

**Outcome-agnostic self-resolution measures in two public debugging datasets**

Replication package for the manuscript by Mikoto Miura

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23029603.svg)](https://doi.org/10.5281/zenodo.23029603)
[![Code: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-blue.svg)](LICENSE)
[![Data and text: CC BY 4.0](https://img.shields.io/badge/data%20and%20text-CC%20BY%204.0-lightgrey.svg)](LICENSE-DATA)
[![Python 3.11+, standard library only](https://img.shields.io/badge/python-3.11%2B%2C%20stdlib%20only-3776AB.svg)](ENV.md)

</div>

---

## Overview

Observational studies of debugging report how often developers consult documentation, the web or other people. The complement, debugging without consultation, is easily read as problems resolved without help. That reading requires every unit without consultation to end in a fix. In the two public, human-coded datasets of professional debugging reanalysed here, however, a unit also ends when the developer stops, and in one of them when observation ends.

This repository defines an **outcome-agnostic** measure and an **outcome-requiring** measure, decomposes their difference exactly, and estimates it under several operational definitions of consultation and resolution. All analysis results reported in the manuscript are produced by the code in this repository.

## The measures

| Measure | Definition |
|---|---|
| R0 | units that ended with no consultation of external resources / all units |
| R0′ | resolved units with no consultation / all units |
| R1 | resolved units with no consultation / resolved units |
| numerator effect | R0 − R0′ = units that ended **unresolved and without consultation** / all units |
| denominator-only effect | R0′ − R1 (same numerator; denominator all → resolved) |
| conditioning effect | R0 − R1 = numerator effect + denominator-only effect |

Units are debugging episodes in D1 and debugging tasks in D2.

## Data

| | Source | What is used |
|---|---|---|
| **D1** | Alaboudi & LaToza: 89 debugging episodes by 11 developers in live-streamed open-source work (arXiv:2105.02162v1; *Empirical Software Engineering* 28:117, 2023) | The shared coding (`rowData.json`); the replication packages linked from the two versions carry the same, byte-identical coding |
| **D2** | Li & Coblenz: 17 debugging tasks by 7 professional developers and 5 streamers (*Proc. ACM Softw. Eng.* 3(FSE):FSE049, 2026) | Table 4, three rows of Table 5 and three sentences of the text, transcribed |

Both sources are released under CC BY 4.0. No raw data is committed: [DATA.md](DATA.md) gives the source, the SHA-256 hash and how to obtain every input.

## Quick start

```bash
git clone https://github.com/mikotomiura/self-resolution-measure.git
cd self-resolution-measure
# D1: download either figshare package in a browser and put the zip in raw/
#     (DATA.md, "How to obtain"; figshare blocks curl and wget with a bot challenge)
bash run.sh
```

Requirements: Python 3.11 or later (standard library only), `bash`, and `sha256sum` or `shasum` ([ENV.md](ENV.md)). Outputs: `results/metrics.json` and `results/report.md`.

### What `run.sh` checks

1. The hashes of all inputs.
2. A self-test: the data gates must fail on absent or broken input, the consultation rules must match a truth table, and synthetic controls must recover known values.
3. The analysis itself.
4. A second run under another hash seed, which must be byte-identical.
5. Equality of the output with the bundled `results/` (compared with `cmp`, so git is not needed; set `ALLOW_RESULT_CHANGE=1` only after an intended change).
6. A record of the hashes of every input and script in `results/provenance.txt`.

### Rebuilding the manuscript

`bash paper/build.sh` fetches the Springer Nature template (checked by SHA-256 and not redistributed), regenerates `paper/results.tex` from `results/metrics.json` and requires it to equal the committed file, and builds `paper/main.pdf` with Tectonic (developed with 0.17.0; it fetches TeX packages over the network on first use). Every analysis number in the text is taken from `results.tex`, and the qualitative statements are checked by `paper/make_results.py` (`--selftest` shows that the checks stop on falsified metrics).

## Freeze and provenance

- The commit history shows that the analysis configuration (`config.json`) was first committed before the analysis code and the results. [NOTES.md](NOTES.md) lists what was known before the freeze (Freeze) and every later change (Deviations).
- The D2 tables were transcribed twice by separate instances of an LLM-based assistant; the two transcriptions are byte-identical and were checked against totals in the paper and against the PDF by the author ([data/li-coblenz-2026/README.md](data/li-coblenz-2026/README.md)).
- An archived copy of version `submission-2026-09-29` is on Zenodo: <https://doi.org/10.5281/zenodo.23029603>.

## Repository layout

| Path | Contents |
|---|---|
| [`config.json`](config.json) | Analysis definitions, first committed before the analysis code and the results |
| [`run.sh`](run.sh) | One-command reproduction and checks |
| [`analysis/`](analysis) | `d1.py` (episode extraction, gate, reproduction of the journal version's figures), `d2.py` (transcriptions, gate), `stats.py` (measures, Wilson intervals, cluster bootstrap), `analyze.py` (entry point) |
| [`data/li-coblenz-2026/`](data/li-coblenz-2026) | Transcriptions of the D2 tables and the three quoted sentences used in a sensitivity analysis |
| [`results/`](results) | `metrics.json`, `report.md`, `provenance.txt` |
| [`paper/`](paper) | Manuscript source (`main.tex`, `refs.bib`), generated `results.tex`, and its build |
| [`NOTES.md`](NOTES.md) | Question, what is not new, the freeze, deviations |
| [`DATA.md`](DATA.md) | Provenance and hashes of every input |
| [`ENV.md`](ENV.md) | Environment |

## Citation

If you use this package, please cite the archived copy:

```bibtex
@misc{miura2026selfresolution,
  author    = {Miura, Mikoto},
  title     = {Replication package for "When 'no help' is not 'solved': outcome-agnostic self-resolution measures in two public debugging datasets"},
  year      = {2026},
  publisher = {Zenodo},
  version   = {submission-2026-09-29},
  doi       = {10.5281/zenodo.23029603}
}
```

## Licence

| Part | Licence |
|---|---|
| Code: `analysis/`, `run.sh`, `paper/build.sh`, `paper/make_results.py` | Apache License 2.0 ([LICENSE](LICENSE)) |
| Data derived here (`data/`, `results/`, `paper/results.tex`), `config.json`, the documentation and the manuscript (`paper/main.tex`, `paper/refs.bib`) | CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)) |
| Sentences and passages quoted from other works (in `config.json`, `results/`, `data/` and the manuscript) | Their original terms |
| Springer Nature template files (`sn-jnl.cls`, `sn-basic.bst`) | Not redistributed; `paper/build.sh` downloads the publisher's package and checks its SHA-256 |

Third-party sources keep their own licences and must be attributed: the Alaboudi & LaToza replication packages (CC BY 4.0; not redistributed here) and the Li & Coblenz paper (CC BY 4.0; its tables are transcribed in [`data/li-coblenz-2026/`](data/li-coblenz-2026/README.md)).
