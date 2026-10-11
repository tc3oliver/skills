class TTLCache:
    def __init__(self,clock):self.clock=clock;self.data={}
    def put(self,key,value,ttl):self.data[key]=(value,self.clock()+ttl)
    def get(self,key):
        value=self.data.get(key)
        if value is None:return None
        item,deadline=value
        if self.clock()>=deadline:
            del self.data[key]
            return None
        return item
