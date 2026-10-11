from tokens import token_start

def mark(text,token):
    start=token_start(text,token)
    if start is None:return text
    end=start+len(token)
    return text[:start]+"["+text[start:end]+"]"+text[end:]
