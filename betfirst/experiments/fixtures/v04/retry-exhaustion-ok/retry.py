def retry_once(operation):
    """Retry a transient TimeoutError at most once; propagate other failures."""
    try:
        return operation()
    except TimeoutError:
        return operation()
