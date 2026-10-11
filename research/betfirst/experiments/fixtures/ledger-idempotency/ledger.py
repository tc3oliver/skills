class Ledger:
    def __init__(self,balances):
        self.balances=dict(balances);self.receipts={}
    def debit(self,account,request_id,amount):
        if amount<=0:raise ValueError("amount")
        if self.balances[account]<amount:raise ValueError("insufficient")
        self.balances[account]-=amount
        receipt=(account,request_id,amount,self.balances[account])
        self.receipts[(account,request_id)]=receipt
        return receipt
