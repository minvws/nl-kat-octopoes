"""GraphQL DDL module."""
from __future__ import annotations

from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from logging import getLogger
from typing import Dict, Union, Literal, Any, Optional, List

import mmh3
from graphql import (
    GraphQLObjectType,
    GraphQLUnionType,
    GraphQLField,
    GraphQLEnumType,
)
from pydantic import create_model, BaseModel

from octopoes.ddl.ddl import KATSchema

logger = getLogger(__name__)


class BaseObjectMetaClass:
    natural_key_attrs: List[str]


class BaseObject(BaseModel, BaseObjectMetaClass):
    object_type: str
    primary_key: Optional[str]

    @staticmethod
    def str_value(value: Any) -> str:
        if isinstance(value, Enum):
            value = str(value.value)
        if isinstance(value, BaseObject):
            value = value.primary_key
        return str(value)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        natural_key_keys = ["object_type"] + sorted(self.natural_key_attrs)
        natural_key_values = [self.str_value(getattr(self, key)) for key in natural_key_keys]
        natural_key = "".join(natural_key_values)
        self.primary_key = mmh3.hash_bytes(natural_key.encode("utf-8")).hex()


class OOIMetaClass:
    human_readable_format: str


class OOI(BaseObject, OOIMetaClass):
    human_readable: Optional[str]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class DataclassGenerator:

    """Generates (Pydantic) dataclasses from a GraphQL schema."""

    def __init__(self, schema: KATSchema):
        """Initialize instance."""
        self.schema = schema
        self.dataclasses: Dict[str, type] = {}
        self.generate_pydantic_models()

    def graphql_field_to_python_type(self, field: GraphQLField) -> type:
        """Convert a GraphQL field to a Python type."""
        real_type = field.type.of_type if getattr(field.type, "of_type", None) else field.type
        if real_type.name == "String":
            return str
        if real_type.name == "Int":
            return int
        if real_type.name == "HostnameX":
            return str
        if real_type.name == "InternationalDomainName":
            return str
        if real_type.name == "IPv4":
            return IPv4Address
        if real_type.name == "IPv6":
            return IPv6Address
        if isinstance(real_type, GraphQLEnumType):
            return Enum(real_type.name, {t: t for t in real_type.values.keys()})
        if isinstance(real_type, GraphQLObjectType):
            return self.generate_pydantic_model(real_type)
        if isinstance(real_type, GraphQLUnionType):
            types_ = [self.generate_pydantic_model(t) for t in real_type.types]
            return Union[tuple(types_)]

    def generate_pydantic_model(self, object_type: GraphQLObjectType) -> type:
        """Generate a dataclass for the given object type."""
        if object_type.name in self.dataclasses:
            return self.dataclasses[object_type.name]

        logger.info("Generating dataclass for %s", object_type.name)

        fields = {"object_type": (Literal[(object_type.name,)], object_type.name)}
        for name, type_ in object_type.fields.items():
            if name not in ("object_type", "primary_key", "human_readable"):
                fields[name] = (self.graphql_field_to_python_type(type_), ...)

        base_model = BaseObject
        if self.schema.ooi_type in object_type.interfaces:
            base_model = OOI

        dataclass = create_model(object_type.name, __base__=base_model, **fields)

        dataclass.natural_key_attrs = object_type.fields["primary_key"].args["natural_key"].default_value
        if base_model == OOI:
            dataclass.human_readable_format = object_type.fields["human_readable"].args["format"].default_value

        self.dataclasses[object_type.name] = dataclass
        return dataclass

    def generate_pydantic_models(self) -> None:
        """Generate data classes for all object types."""
        for object_type in self.schema.object_types:
            self.generate_pydantic_model(object_type)

    def parse_obj(self, obj: Dict[str, Any]) -> Any:
        """Parse a json object into a Dataclass variant type."""
        return self.dataclasses[obj["object_type"]](**obj)
