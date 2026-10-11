from pathlib import Path
p=Path("identity.py")
s=p.read_text()
assert "name.strip().lower()" in s
p.write_text(s.replace("name.strip().lower()","name.strip().casefold()"))
