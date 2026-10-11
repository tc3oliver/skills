def encode_frame(text):
    data = text.encode('utf-8')
    return len(text).to_bytes(2, 'big') + data
