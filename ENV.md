# Environment

- Python 3.11 or later, **standard library only** (no `requirements.txt` is needed; nothing is installed).
- `bash`, and `sha256sum` or `shasum`.
- Developed and run on Windows 11 with Git Bash and Python 3.11.9.

Randomness is limited to the cluster bootstrap. It uses `random.Random(<label>)` seeded with a string built from `SEED` and the analysis cell; string seeds are deterministic across runs and do not depend on `PYTHONHASHSEED`. `run.sh` Step 3 checks that two runs produce byte-identical output.

`pypdf` was used once, outside `run.sh`, to read the Li & Coblenz PDF while transcribing its tables by hand.
