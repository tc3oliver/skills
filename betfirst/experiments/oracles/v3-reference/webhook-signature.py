from pathlib import Path
p=Path("verify.py")
s=p.read_text()
assert "hmac.compare_digest(expected,signature)" in s
p.write_text(s.replace("hmac.compare_digest(expected,signature)","hmac.compare_digest('sha256='+expected,signature)"))
