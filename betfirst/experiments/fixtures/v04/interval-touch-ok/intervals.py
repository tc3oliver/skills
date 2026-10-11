def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """True only when the half-open intervals [start,end) share a point."""
    if a_end < a_start or b_end < b_start:
        raise ValueError("reversed interval")
    return max(a_start,b_start) < min(a_end,b_end)
