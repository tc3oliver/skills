class Watermarks:
    def __init__(self):self.offset=0
    def accept(self,partition,offset):
        if offset<=self.offset:return False
        self.offset=offset
        return True
