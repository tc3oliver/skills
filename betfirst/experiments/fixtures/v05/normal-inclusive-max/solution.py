def clamp(x, low, high):
    if x <= low: return low
    if x >= high: return high-1
    return x
