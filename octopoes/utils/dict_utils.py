"""Dict utitilies."""
from typing import Any, List, Optional, Dict, MutableMapping, Tuple


def deep_get(data: Optional[Any], keys: List[str]) -> Any:
    """Get a value from a nested dict using a list of keys."""
    if not keys or data is None:
        return data
    return deep_get(data.get(keys[0]), keys[1:])


def flatten(d: MutableMapping[str, Any], parent_key: str = "", sep: str = "_") -> MutableMapping[str, Any]:
    items: List[Tuple[str, Any]] = []
    for key, value in d.items():
        new_key = parent_key + sep + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))
    return dict(items)
