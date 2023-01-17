from typing import Any, List, Optional


def deep_get(d: Optional[Any], keys: List[str]) -> Any:
    if not keys or d is None:
        return d
    return deep_get(d.get(keys[0]), keys[1:])

