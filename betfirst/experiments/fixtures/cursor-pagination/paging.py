def page(records, cursor=0, limit=2):
    if not isinstance(limit,int) or limit<1: raise ValueError("limit")
    if not isinstance(cursor,int) or cursor<0 or cursor>len(records): raise ValueError("cursor")
    end=min(cursor+limit+1,len(records))
    out=list(records[cursor:end])
    next_cursor=end if end<len(records) else None
    return out,next_cursor
