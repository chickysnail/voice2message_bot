import os


def file_size(path: str | None) -> int:
    """Size of a file in bytes, or 0 if there is no such file."""
    try:
        return os.path.getsize(path) if path else 0
    except OSError:
        return 0
