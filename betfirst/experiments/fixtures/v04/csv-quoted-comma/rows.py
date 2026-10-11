def parse_row(line: str) -> list[str]:
    """Parse one CSV record; preserve an empty final column."""
    return line.rstrip("\r\n").split(",")
