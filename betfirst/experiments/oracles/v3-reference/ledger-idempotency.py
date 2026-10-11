from pathlib import Path
p=Path("ledger.py")
s=p.read_text()
assert "        if self.balances[account]<amount:raise ValueError(\"insufficient\")" in s
p.write_text(s.replace("        if self.balances[account]<amount:raise ValueError(\"insufficient\")","        key=(account,request_id)\n        if key in self.receipts:\n            receipt=self.receipts[key]\n            if receipt[2]!=amount:raise ValueError(\"request id reused with different amount\")\n            return receipt\n        if self.balances[account]<amount:raise ValueError(\"insufficient\")"))
