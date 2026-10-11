def token_start(text,token):
    i=text.find(token)
    if i<0:return None
    return len(text[:i].encode("utf-8"))
