def is_under(path: str, prefix: str) -> bool:
    """Whether the URL path is at or below a route prefix."""
    return path.startswith(prefix)
