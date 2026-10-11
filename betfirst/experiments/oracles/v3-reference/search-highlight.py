from pathlib import Path
p=Path("tokens.py")
s=p.read_text()
assert "len(text[:i].encode(\"utf-8\"))" in s
p.write_text(s.replace("len(text[:i].encode(\"utf-8\"))","i"))
