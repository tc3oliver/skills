def normalize_user(name: str) -> str:
    if not isinstance(name,str):raise TypeError("name")
    return name.strip().lower()

def matches(a,b):return normalize_user(a)==normalize_user(b)
