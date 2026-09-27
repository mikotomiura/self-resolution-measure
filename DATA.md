# Data provenance

No raw data is committed to this repository. `raw/` is git-ignored; `run.sh` refuses to run unless the D1 input matches the SHA-256 values below. The D2 transcriptions are tracked files; their hashes are recorded in `results/provenance.txt`.

## D1 — Alaboudi & LaToza, live-streamed debugging episodes

| | |
|---|---|
| Papers | arXiv:2105.02162v1 (2021) and its journal version, *Empirical Software Engineering* 28:117 (2023), doi:10.1007/s10664-023-10352-5 |
| Licence | CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ (shown on both figshare item pages) |
| Coding | 15 sessions, 11 developers, 89 debugging episodes. The first author coded the whole dataset; two authors calibrated on 20 episodes / 166 activities (Cohen's kappa 75% / 84%, per the papers). |

Two replication packages are linked from the two versions of the paper. **Their `rowData.json` and codebook are byte-identical** (checked 2026-09-28):

| Package | Linked from | figshare file | Size (B) | SHA-256 of zip |
|---|---|---|---|---|
| `replication_package_FSE2021.zip` | arXiv v1, footnote 4 (`https://figshare.com/s/6c4026a941db49ea3de3`) | 26553647 | 182,303 | `6f506cba88ef30a7027b367967a6d92628c84e90d80b4a1a343190e1083d04b2` |
| `Replication_Debugging.zip` (item modified 2021-09-04) | EMSE 2023 reference list (`https://figshare.com/s/0e9eac98b8ddd54c384c`) | 30646101 | 218,759 | `523705d8f02f59bfe952328598f03ee28f1d2c8f2a5e3a26caf2d251c8108fe4` |

| File inside | SHA-256 | In v1 zip | In EMSE zip |
|---|---|---|---|
| `rowData.json` (2,306,479 B) | `497df0b4da398c39cc0fd8b28544d4ac1d61c728708f4f9cdaa32469acda78b9` | yes | yes |
| codebook PDF (63,231 B) | `0a1cc4cbe9224fff87c8a4bc85bfa7eeee4052203e5df578d2ef124cfd35a197` | `codingBookFSE2021.pdf` | `codingBook.pdf` |
| `Observe-devOnlineDataSetLink.txt` | `a3e63be1fbfdb9fc53174903d05bf1f417faf5fc3927137f9938a819aa712683` | yes | yes |
| `interviews .pdf` (43,886 B; interview study of the EMSE version) | `2594cbc5eacc48facecc97bc46b616cda349e7406f40487bc01ea9493da9f9e0` | no | yes |

The EMSE version reports different figures for the same episodes (2135 activities; consultation in 33% of episodes). We could not derive all of them from the shared coding under any of the four consultation rules we examined, and we could not determine how they were obtained; `run.sh` reports how far each figure can be reproduced from the shared public coding (see `results/report.md`).

The dataset site named in both papers (`observe-dev.online`) no longer resolves (NXDOMAIN, checked 2026-09-06). figshare is the only surviving source and serves only through private links, which are not indexed by the figshare API or search.

### How to obtain

figshare answers `curl`/`wget` with a bot challenge (HTTP 202 with 0 bytes, or 403). Use a real browser:

1. Open either private link above and press *Download*.
2. Put the zip in `raw/` (either one is enough; both contain the same `rowData.json`).
3. Run `bash run.sh`. It checks the zip hash, extracts `rowData.json` to `raw/rowData.json`, and checks its hash.

The data contain per-session URLs of public videos and repositories. Outputs of this repository contain aggregate counts only.

## D2 — Li & Coblenz, debugging tasks in professional practice

| | |
|---|---|
| Paper | *Proc. ACM Softw. Eng.* 3(FSE), Article FSE049 (2026), doi:10.1145/3797077; arXiv:2602.11435v3 |
| Licence | CC BY 4.0 (stated on the first page of the paper) |
| What is used | Table 4 (task, time, `Resolved`) and Table 5 (debugging techniques × task), transcribed twice, independently, with an LLM-based assistant (see `data/li-coblenz-2026/README.md`); three sentences of body text (`data/li-coblenz-2026/text_external.csv`) |
| PDF used for transcription | arXiv:2602.11435v3, 911,582 B, SHA-256 `4b3ba562ae43c845dcba37845503cd199a79a781b8bb5670991793785352337f` (identical when downloaded on 2026-09-27 and 2026-09-28) |

The authors' supplementary spreadsheets on GitHub are **not** used: that repository carries no licence.

Transcription was done twice, independently (`transcription_a.csv`, `transcription_b.csv`). `run.sh` requires the two files to agree cell by cell and checks them against totals stated elsewhere in the paper (`config.json` → `d2.gate`).
