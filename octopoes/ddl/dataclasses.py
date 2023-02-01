"""GraphQL DDL module."""
from __future__ import annotations

from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from logging import getLogger
from typing import Dict, Union, Literal, Any, Optional, List, Iterator, Type, cast

import mmh3
from graphql import (
    GraphQLObjectType,
    GraphQLUnionType,
    GraphQLField,
    GraphQLEnumType,
)
from pydantic import create_model, BaseModel

from octopoes.ddl.ddl import KATSchema
from octopoes.utils.dict_utils import flatten

logger = getLogger(__name__)


class BaseObjectMetaClass:
    natural_key_attrs: List[str]
    human_readable_format: str


class BaseObject(BaseModel, BaseObjectMetaClass):
    object_type: str
    primary_key: Optional[str]
    human_readable: Optional[str]

    @staticmethod
    def str_value(value: Any) -> str:
        if isinstance(value, Enum):
            value = str(value.value)
        if isinstance(value, BaseObject):
            value = value.primary_key
        return str(value)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        natural_key_keys = ["object_type"] + sorted(self.natural_key_attrs)
        natural_key_values = [self.str_value(getattr(self, key)) for key in natural_key_keys]
        natural_key = "".join(natural_key_values)
        self.primary_key = mmh3.hash_bytes(natural_key.encode("utf-8")).hex()

        self.human_readable = self.human_readable_format.format(**flatten(self.dict()))

    @property
    def sub_objects(self) -> Iterator[BaseObject]:
        for key, value in self:
            if isinstance(value, BaseObject):
                yield from value.sub_objects
        yield self

    class Config:
        use_enum_values = True


class OOI(BaseObject):
    ...


class DataclassGenerator:

    """Generates (Pydantic) dataclasses from a GraphQL schema."""

    def __init__(self, schema: KATSchema):
        """Initialize instance."""
        self.schema = schema
        self.dataclasses: Dict[str, Type[BaseObject]] = {}
        self.generate_pydantic_models()

    def graphql_field_to_python_type(self, field: GraphQLField) -> Any:
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

    def generate_pydantic_model(self, object_type: GraphQLObjectType) -> Type[BaseObject]:
        """Generate a dataclass for the given object type."""
        if object_type.name in self.dataclasses:
            return self.dataclasses[object_type.name]

        logger.info("Generating dataclass for %s", object_type.name)

        fields = {"object_type": (Literal[(object_type.name,)], object_type.name)}
        for name, type_ in object_type.fields.items():
            if name not in ("object_type", "primary_key", "human_readable"):
                fields[name] = (self.graphql_field_to_python_type(type_), ...)

        base_model: Type[BaseObject] = BaseObject
        if self.schema.ooi_type in object_type.interfaces:
            base_model = OOI

        dataclass = create_model(object_type.name, __base__=base_model, **fields)  # type: ignore

        dataclass.natural_key_attrs = object_type.fields["primary_key"].args["natural_key"].default_value
        dataclass.human_readable_format = object_type.fields["human_readable"].args["format"].default_value

        self.dataclasses[object_type.name] = dataclass
        return cast(Type[BaseObject], dataclass)

    def generate_pydantic_models(self) -> None:
        """Generate data classes for all object types."""
        for object_type in self.schema.object_types:
            self.generate_pydantic_model(object_type)

    def parse_obj(self, obj: Dict[str, Any]) -> Any:
        """Parse a json object into a Dataclass variant type."""
        return self.dataclasses[obj["object_type"]](**obj)
