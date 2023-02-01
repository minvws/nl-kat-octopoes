"""GraphQL DDL module."""
from __future__ import annotations

from functools import cached_property
from logging import getLogger
from pathlib import Path
from typing import cast, Optional

from graphql import (
    build_schema,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLSchema,
    GraphQLUnionType,
    GraphQLField,
    GraphQLList,
    GraphQLEnumType,
    GraphQLString,
    GraphQLID,
    extend_schema,
    parse,
    GraphQLArgument,
)

logger = getLogger(__name__)


class SchemaValidationException(Exception):
    """Exception raised when a schema is invalid."""


# Types that are already used by the GraphQL library and should not be used in KAT schemas
BUILTIN_TYPES = {
    "String",
    "Int",
    "Float",
    "Boolean",
    "ID",
    "__Schema",
    "__Type",
    "__TypeKind",
    "__Field",
    "__InputValue",
    "__EnumValue",
    "__Directive",
    "__DirectiveLocation",
}

BUILTIN_DIRECTIVES = {
    "skip",
    "include",
    "deprecated",
    "specifiedBy",
}


KAT_DIRECTIVES = {
    "constraint",
    "natural_key",
    "format",
    "reverse_name",
}


RESERVED_KEYWORDS = {
    "Query",
    "Mutation",
}


BASE_SCHEMA_FILE = Path(__file__).parent / "schemas" / "base_schema.graphql"
OPENKAT_SCHEMA_FILE = Path(__file__).parent / "schemas" / "openkat_schema.graphql"


class OpenKATSchema:
    """Wrapper for a KAT GraphQLSchema."""

    def __init__(self, schema: GraphQLSchema) -> None:
        """Initialize instance."""
        self.schema = schema

    @property
    def base_object_type(self) -> GraphQLInterfaceType:
        """Return the BaseObject type."""
        return cast(GraphQLInterfaceType, self.schema.type_map["BaseObject"])

    @property
    def ooi_type(self) -> GraphQLInterfaceType:
        """Return the OOI type."""
        return cast(GraphQLInterfaceType, self.schema.type_map["OOI"])

    @property
    def object_types(self) -> list[GraphQLObjectType]:
        """Return all object types."""
        return [
            t for t in self.schema.type_map.values() if isinstance(t, GraphQLObjectType) and not t.name.startswith("__")
        ]


class SchemaLoader:
    """Loads the OpenKAT schema definition to validate and calculate the derived, hydrated schemas."""

    def __init__(self, openkat_schema_definition: Optional[str] = None):
        """Initialize instance."""
        self.openkat_schema_definition = openkat_schema_definition \
            if openkat_schema_definition is not None \
            else OPENKAT_SCHEMA_FILE.read_text()
        self.validate_openkat_schema()

    @cached_property
    def base_schema(self) -> OpenKATSchema:
        """Return and cache the base schema."""
        return OpenKATSchema(build_schema(BASE_SCHEMA_FILE.read_text()))

    @cached_property
    def openkat_schema(self) -> OpenKATSchema:
        """Load the schema from disk."""
        return OpenKATSchema(extend_schema(self.base_schema.schema, parse(self.openkat_schema_definition)))

    def validate_openkat_schema(self) -> None:
        """Validate the schema."""
        # Validate directives, no custom directives are allowed
        directive_names = {d.name for d in self.openkat_schema.schema.directives}
        if directive_names - BUILTIN_DIRECTIVES - KAT_DIRECTIVES:
            raise SchemaValidationException("Custom directives are not allowed")

        # Validate object types
        for type_ in self.openkat_schema.schema.type_map.values():
            if type_.name in BUILTIN_TYPES:
                continue

            if type_ in (self.openkat_schema.ooi_type, self.openkat_schema.base_object_type):
                continue

            if type_.name in RESERVED_KEYWORDS:
                raise SchemaValidationException(f"{type_.name} is a reserved keyword")

            if isinstance(type_, GraphQLObjectType):
                if self.openkat_schema.base_object_type not in type_.interfaces:
                    raise SchemaValidationException(f"Object type must implement base types [type={type_.name}]")
                if self.openkat_schema.ooi_type not in type_.interfaces:
                    raise SchemaValidationException(f"Object type must implement base types [type={type_.name}]")

    @cached_property
    def full_schema(self) -> GraphQLSchema:
        """Build the full schema.

        Combines all concrete types into a single union type.
        Defines the root query type, based on above union type.
        """
        # OOI Union = all object types that implement OOI
        ooi_union = GraphQLUnionType("UOOI", types=self.openkat_schema.object_types)

        # Construct Scan Profile Type
        scan_level = GraphQLEnumType("ScanLevel", values={"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4})
        scan_profile_type = GraphQLEnumType(
            "ScanProfileType", values={"empty": "empty", "declared": "declared", "inherited": "inherited"}
        )
        scan_profile = GraphQLObjectType(
            "ScanProfile",
            fields={
                "object_type": GraphQLField(GraphQLString),
                "primary_key": GraphQLField(
                    GraphQLID, args={"natural_key": GraphQLArgument(GraphQLList(GraphQLString), default_value=["ooi"])}
                ),
                "type": GraphQLField(scan_profile_type),
                "level": GraphQLField(scan_level),
                "ooi": GraphQLField(ooi_union),
            },
            interfaces=[self.openkat_schema.base_object_type],
        )

        # Construct Query Type
        query = GraphQLObjectType("Query", fields={"OOI": GraphQLField(GraphQLList(ooi_union))})

        full_schema_kwargs = self.openkat_schema.schema.to_kwargs()
        full_schema_kwargs["query"] = query
        full_schema_kwargs["types"] = full_schema_kwargs["types"] + (ooi_union, scan_profile, query)

        return GraphQLSchema(**full_schema_kwargs)
