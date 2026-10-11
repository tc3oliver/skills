from pathlib import Path
p=Path("watermarks.py")
s=p.read_text()
s=s.replace("self.offset=0","self.offsets={}")
s=s.replace("if offset<=self.offset:return False\n        self.offset=offset","if offset<=self.offsets.get(partition,-1):return False\n        self.offsets[partition]=offset")
p.write_text(s)
