from pathlib import Path
p=Path("lease.py")
s=p.read_text()
assert "if active is None or active[0]!=owner:raise ValueError(\"not owner\")" in s
p.write_text(s.replace("if active is None or active[0]!=owner:raise ValueError(\"not owner\")","if active is None or active[0]!=owner or active[1]!=token or now>=active[2]:raise ValueError(\"stale lease\")"))
