"""Deterministic harness smoke driver, NOT a language model or policy evaluation."""
from pathlib import Path
import sys

task_id = sys.argv[1]
file = Path("lib.py")
if task_id == "subtitle-path":
    file.write_text(
        "def subtitle_filter_path(raw):\n"
        "    return raw.replace(chr(92), '/').replace(':', chr(92) + ':')\n",
        encoding="utf-8",
    )
elif task_id == "tts-estimate":
    file.write_text(
        "def estimate_seconds(characters):\n"
        "    return round(characters / 5.0)\n",
        encoding="utf-8",
    )
elif task_id == "already-correct":
    pass
else:
    raise SystemExit("unknown smoke task " + task_id)
print("SYNTHETIC HARNESS SMOKE ONLY; NOT AN AGENT RESULT")
