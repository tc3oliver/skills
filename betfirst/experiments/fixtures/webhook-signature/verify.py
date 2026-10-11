import hashlib, hmac, re

def verify(secret: bytes, body: bytes, signature: str) -> bool:
    if not isinstance(signature,str) or re.fullmatch(r"sha256=[0-9a-f]{64}", signature) is None:
        return False
    expected=hmac.new(secret,body,hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected,signature)
