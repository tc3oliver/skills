def decode_chunks(chunks):
    """Decode complete length-prefixed frames, returning frames and remainder."""
    buf = b"".join(chunks)
    frames = []
    pos = 0
    while pos + 2 <= len(buf):
        size = int.from_bytes(buf[pos:pos+2], "big")
        if pos + 2 + size > len(buf):
            break
        frames.append(buf[pos+2:pos+2+size])
        pos += 2 + size
    return frames, buf[pos:]
