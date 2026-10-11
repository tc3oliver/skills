from ledger import Ledger

def post_debit(ledger:Ledger,account,request_id,amount):
    return ledger.debit(account,request_id,amount)
