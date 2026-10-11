from solution import encode_frame
for s in ('', 'abc', 'é', '🧪', 'a🧪z'):
    b=encode_frame(s)
    assert int.from_bytes(b[:2],'big') == len(s.encode('utf-8'))
    assert b[2:].decode('utf-8') == s
