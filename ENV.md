# Environment

- Python 3.11 or later, **standard library only** (no `requirements.txt` is needed; nothing is installed).
- `bash`, and `sha256sum` or `shasum`.
- Developed and run on Windows 11 with Git Bash and Python 3.11.9.

Randomness is limited to the cluster bootstrap. It uses `random.Random(<label>)` seeded with a string built from `SEED` and the analysis cell; string seeds are deterministic across runs and do not depend on `PYTHONHASHSEED`. `run.sh` Step 3 runs the analysis twice with `PYTHONHASHSEED=0` and `=1` and requires byte-identical output; Step 4 requires the output to equal the committed `results/`.

`pypdf` was used outside `run.sh` to extract the text of the Li & Coblenz PDF for transcription (see `data/li-coblenz-2026/README.md`).
