"""The framing spec: a 2-byte unsigned little-endian payload length."""
def frame(payload: bytes) -> bytes:
    if len(payload) > 65535:
        raise ValueError("payload too large")
    return len(payload).to_bytes(2, "little") + payload
