from pathlib import Path
p=Path("paging.py")
s=p.read_text()
assert "cursor+limit+1" in s
p.write_text(s.replace("cursor+limit+1","cursor+limit"))
