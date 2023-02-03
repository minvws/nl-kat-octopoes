"""Repository to save/looad Octopoes objects to XTDB."""
import json
import logging
from datetime import timezone, datetime
from typing import Any, Dict

from graphql import GraphQLObjectType

from octopoes.connectors.services.xtdb import XTDBHTTPClient, XTDBSession, OperationType
from octopoes.ddl.dataclasses import BaseObject, DataclassGenerator
from octopoes.ddl.ddl import SchemaLoader

logger = logging.getLogger(__name__)


class ObjectRepository:
    """Repository to save/load Octopoes objects to XTDB."""

    def __init__(
        self, schema: SchemaLoader, dataclass_generator: DataclassGenerator, xtdb_client: XTDBHTTPClient
    ) -> None:
        """Initialize the object repository."""
        self.schema = schema
        self.dataclass_generator = dataclass_generator
        self.xtdb_client = xtdb_client

    @staticmethod
    def rm_prefixes(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Strip property prefixes from XTDB object."""
        obj.pop("xt/id")
        # remove prefix from prefixed fields
        data = {key.split("/")[1]: value for key, value in obj.items() if "/" in key}
        data.update({key: value for key, value in obj.items() if "/" not in key})
        return data

    @staticmethod
    def prefix_fields(obj: Dict[str, Any]) -> Dict[str, Any]:
        """Prefix fields with object_type."""
        non_prefixed_fields = ["object_type", "primary_key", "human_readable"]
        object_type, primary_key, human_readable = [obj.pop(key) for key in non_prefixed_fields]

        export = {f"{object_type}/{key}": value for key, value in obj.items()}

        export["object_type"] = object_type
        export["primary_key"] = primary_key
        export["human_readable"] = human_readable
        export["xt/id"] = primary_key

        return export

    @staticmethod
    def serialize_obj(obj: BaseObject) -> Dict[str, Any]:
        """Serialize an object to a dict for XTDB."""
        pk_overrides = {}
        for key, value in obj:
            if isinstance(value, BaseObject):
                pk_overrides[key] = value.primary_key

        # export model with pydantic serializers
        export: Dict[str, Any] = json.loads(obj.json())
        export.update(pk_overrides)

        export = ObjectRepository.prefix_fields(export)

        return export

    def get(self, primary_key: str) -> Dict[str, Any]:
        """Get an object from XTDB by primary key. Primary key objects are hydrated."""
        obj_data = self.rm_prefixes(self.xtdb_client.get_entity(primary_key))

        object_cls = self.dataclass_generator.dataclasses[obj_data["object_type"]]
        graphql_cls: GraphQLObjectType = self.schema.hydrated_schema.schema.get_type(obj_data["object_type"])

        for key, value in obj_data.items():
            if key in object_cls.natural_key_attrs and self.dataclass_generator.is_field_foreign_key(  # type: ignore
                graphql_cls.fields[key]
            ):
                obj_data[key] = self.get(value)

        return obj_data

    def save(self, obj: BaseObject) -> None:
        """Save an object to XTDB."""
        xtdb_session = XTDBSession(self.xtdb_client)
        for obj_ in obj.dependencies():
            xtdb_session.add((OperationType.PUT, self.serialize_obj(obj_), datetime.now(timezone.utc)))
        xtdb_session.commit()
