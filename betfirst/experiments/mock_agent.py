"""Deterministic harness smoke driver, NOT a language model or policy evaluation."""
from pathlib import Path
import sys

task_id = sys.argv[1]
file = Path("lib.py")
if task_id == "subtitle-path":
    file.write_text(
        "def subtitle_filter_path(raw):\n"
        "    path = raw.replace(chr(92), '/')\n"
        "    if len(path) >= 2 and path[0].isalpha() and path[1] == ':':\n"
        "        path = path[0] + chr(92) + ':' + path[2:]\n"
        "    return path\n",
        encoding="utf-8",
    )
elif task_id == "tts-estimate":
    file.write_text(
        "def estimate_seconds(characters):\n"
        "    return round(characters / 5.0)\n",
        encoding="utf-8",
    )
elif task_id == "config-scope":
    file = Path("service.py")
    content = file.read_text(encoding="utf-8")
    assert "cache_key = flag" in content
    file.write_text(content.replace("cache_key = flag", "cache_key = (tenant, flag)"), encoding="utf-8")
elif task_id == "render-resume":
    file = Path("pipeline.py")
    content = file.read_text(encoding="utf-8")
    assert "key = segment.title" in content
    assert "manifest.read(segment.title)" in content
    file.write_text(
        content.replace("key = segment.title", "key = segment.segment_id")
               .replace("manifest.read(segment.title)", "manifest.read(segment.segment_id)"),
        encoding="utf-8",
    )
elif task_id == "already-correct":
    pass
else:
    raise SystemExit("unknown smoke task " + task_id)
print("SYNTHETIC HARNESS SMOKE ONLY; NOT AN AGENT RESULT")
