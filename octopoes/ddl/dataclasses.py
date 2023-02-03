"""GraphQL DDL module."""
from __future__ import annotations

from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from logging import getLogger
from typing import Dict, Union, Literal, Any, Optional, List, Iterator, Type

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


class BaseObjectMeta:
    """Metaclass for BaseObject.

    Provide the class attributes in a separate class to avoid Pydantic Metaclass
    """

    _natural_key_attrs: List[str]
    _human_readable_format: str

    @property
    def natural_key_attrs(self) -> List[str]:
        """Make natural_key_attrs public."""
        return self._natural_key_attrs

    @property
    def human_readable_format(self) -> str:
        """Make human_readable_format public."""
        return self._human_readable_format


class BaseObject(BaseModel, BaseObjectMeta):
    """Base class for all database objects."""

    object_type: str
    primary_key: Optional[str]
    human_readable: Optional[str]

    @staticmethod
    def str_value(value: Any) -> str:
        """Convert a value to a string."""
        if isinstance(value, Enum):
            value = str(value.value)
        if isinstance(value, BaseObject):
            value = value.primary_key
        return str(value)

    def __init__(self, **kwargs: Any) -> None:
        """Initialize instance."""
        super().__init__(**kwargs)

        natural_key_keys = ["object_type"] + sorted(self._natural_key_attrs)
        natural_key_values = [self.str_value(getattr(self, key)) for key in natural_key_keys]
        natural_key = "".join(natural_key_values)
        self.primary_key = mmh3.hash_bytes(natural_key.encode("utf-8")).hex()

        self.human_readable = self._human_readable_format.format(**flatten(self.dict()))

    def dependencies(self, include_self: bool = True) -> Iterator[BaseObject]:
        """Return a list of dependencies for this object."""
        for _, value in self:
            if isinstance(value, BaseObject):
                yield from value.dependencies()
        if include_self:
            yield self

    class Config:
        """Pydantic config."""

        use_enum_values = True


class OOI(BaseObject):
    """Object of Interest dataclass."""


class DataclassGenerator:
    """Generates (Pydantic) dataclasses from a GraphQL schema."""

    def __init__(self, schema: KATSchema):
        """Initialize instance."""
        self.schema = schema
        self.dataclasses: Dict[str, Type[BaseObject]] = {}
        self.generate_pydantic_models()

    @staticmethod
    def is_field_foreign_key(field: GraphQLField) -> bool:
        """Check if a field is a foreign key."""
        real_type = field.type.of_type if getattr(field.type, "of_type", None) else field.type
        return isinstance(real_type, (GraphQLObjectType, GraphQLUnionType))

    def graphql_field_to_python_type(  # pylint: disable=too-many-return-statements, inconsistent-return-statements
        self, field: GraphQLField
    ) -> Any:
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

        dataclass: Type[BaseObject] = create_model(object_type.name, __base__=base_model, **fields)  # type: ignore

        dataclass._natural_key_attrs = (  # pylint: disable=protected-access
            object_type.fields["primary_key"].args["natural_key"].default_value
        )
        dataclass._human_readable_format = (  # pylint: disable=protected-access
            object_type.fields["human_readable"].args["format"].default_value
        )

        self.dataclasses[object_type.name] = dataclass
        return dataclass

    def generate_pydantic_models(self) -> None:
        """Generate data classes for all object types."""
        for object_type in self.schema.object_types:
            self.generate_pydantic_model(object_type)

    def parse_obj(self, obj: Dict[str, Any]) -> Any:
        """Parse a json object into a Dataclass variant type."""
        return self.dataclasses[obj["object_type"]](**obj)
