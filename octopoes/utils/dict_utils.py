"""Dict utitilies."""
from typing import Any, List, Optional


def deep_get(data: Optional[Any], keys: List[str]) -> Any:
    """Get a value from a nested dict using a list of keys."""
    if not keys or data is None:
        return data
    return deep_get(data.get(keys[0]), keys[1:])
