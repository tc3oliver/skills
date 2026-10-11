from watermarks import Watermarks

def consume(events,watermarks=None):
    watermarks=watermarks or Watermarks();out=[]
    for partition,offset,value in events:
        if watermarks.accept(partition,offset):out.append(value)
    return out
