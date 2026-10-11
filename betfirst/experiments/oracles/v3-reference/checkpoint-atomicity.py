from pathlib import Path
p=Path("worker.py")
s=p.read_text()
assert "        checkpoint.advance(index+1)\n        sink(items[index])" in s
p.write_text(s.replace("        checkpoint.advance(index+1)\n        sink(items[index])","        sink(items[index])\n        checkpoint.advance(index+1)"))
