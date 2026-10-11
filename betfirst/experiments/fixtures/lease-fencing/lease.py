class LeaseStore:
    def __init__(self):self.leases={};self.results={};self.counter=0
    def acquire(self,key,owner,now,ttl):
        active=self.leases.get(key)
        if active is not None and now<active[2]:return None
        self.counter+=1
        lease=(owner,self.counter,now+ttl)
        self.leases[key]=lease
        return lease[1]
    def commit(self,key,owner,token,result,now):
        active=self.leases.get(key)
        if active is None or active[0]!=owner:raise ValueError("not owner")
        self.results[key]=result
        return result
