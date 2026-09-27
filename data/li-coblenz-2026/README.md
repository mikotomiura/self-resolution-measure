# Transcribed tables from Li & Coblenz (2026)

Source: Haolin Li and Michael Coblenz. 2026. *A Grounded Theory of Debugging in Professional Software Engineering Practice.* Proc. ACM Softw. Eng. 3, FSE, Article FSE049. https://doi.org/10.1145/3797077 (arXiv:2602.11435v3). ©2026 Copyright held by the owner/author(s). Licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

| File | What | Changes made |
|---|---|---|
| `transcription_a.csv`, `transcription_b.csv` | Table 4 (task, time, `Resolved`) and the `documentation`, `social-technical sources` and `web sources` rows of Table 5, one row per task | Values transcribed without change. Times converted from "h min" to minutes. Table 5's grouped task lists (e.g. `P5TA/B/C`) expanded to one flag per task. |
| `text_external.csv` | Three sentences quoted from Sections 4.2.3 and 4.3.1 that describe consultations not listed in Table 5 | Quoted verbatim; task IDs assigned where the developer has only one task in Table 4. |

## How the transcriptions were made

Both transcriptions were produced with an LLM-based coding assistant (Anthropic Claude), not by two people:

- **A**: the assistant session that ran the analysis, reading text extracted from the PDF with `pypdf`.
- **B**: a separate assistant instance given only the PDF (no access to A, to the repository or to the analysis), which extracted the text itself.

The two files are byte-identical, and `run.sh` also checks them against totals stated elsewhere in the paper (`config.json` → `d2.gate`). Because A and B come from the same model, their agreement guards against slips, not against a misreading both instances share; the totals check is the independent safeguard. The body-text additions in `text_external.csv` were likewise identified by A and, independently, by B (B listed the same two tasks, P1TA and S5TA).

The same sentence that mentions S5 also mentions S3 ("(S3, S5)"). S3TA is not listed in `text_external.csv` because Table 5 already lists it under social-technical sources. A documentation mention of "S4" is not listed because S4 has two tasks and the sentence does not say which; Table 5 lists S4TB.

These derived files are released under CC BY 4.0, with the attribution above.
