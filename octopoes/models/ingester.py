from typing import Optional

from pydantic import BaseModel


class Ingester(BaseModel):
    """Representation of a ingesters.Ingester instance. Used for
    unmarshalling of ingesters to a JSON representation."""

    id: Optional[str]
