"""GraphQL DDL module."""
from __future__ import annotations

from functools import cached_property
from logging import getLogger
from pathlib import Path
from typing import cast

from graphql import (
    build_schema,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLSchema,
    print_type,
    GraphQLUnionType,
    GraphQLField,
    GraphQLList,
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


class SchemaManager:
    """Manages a GraphQL schema.

    Loads a schema definition. Validates the schema and derives the full schema, like the root query type.
    """

    def __init__(self, schema_definition: str):
        """Initialize the schema manager."""
        schema = build_schema(schema_definition)
        self.schema = schema
        self.full_schema = self.build_full_schema()
        self.validate(schema)

    @staticmethod
    def load_from_disk() -> SchemaManager:
        """Load the schema from disk."""
        return SchemaManager(OPENKAT_SCHEMA_FILE.read_text())

    @cached_property
    def base_schema(self) -> GraphQLSchema:
        """Return and cache the base schema."""
        return build_schema(BASE_SCHEMA_FILE.read_text())

    def validate(self, new_schema: GraphQLSchema) -> None:
        """Validate the schema."""
        ooi_type = cast(GraphQLInterfaceType, self.base_schema.type_map["OOI"])
        base_type = cast(GraphQLInterfaceType, self.base_schema.type_map["BaseObject"])

        # Validate root types
        if "OOI" not in new_schema.type_map:
            raise SchemaValidationException("Schema must contain OOI interface")

        if "BaseObject" not in new_schema.type_map:
            raise SchemaValidationException("Schema must contain BaseObject interface")

        new_ooi_type = cast(GraphQLInterfaceType, new_schema.type_map["OOI"])
        new_base_type = cast(GraphQLInterfaceType, new_schema.type_map["BaseObject"])

        if print_type(new_ooi_type) != print_type(ooi_type):
            raise SchemaValidationException(f"{ooi_type.name} must equal orginal type")

        if print_type(new_base_type) != print_type(base_type):
            raise SchemaValidationException(f"{base_type.name} must equal orginal type")

        # Validate directives, no custom directives are allowed
        directive_names = {d.name for d in new_schema.directives}
        if directive_names - BUILTIN_DIRECTIVES - KAT_DIRECTIVES:
            raise SchemaValidationException("Custom directives are not allowed")

        # Validate object types
        for type_ in new_schema.type_map.values():
            if type_.name in BUILTIN_TYPES:
                continue

            if type_ in (new_ooi_type, new_base_type):
                continue

            if type_.name in RESERVED_KEYWORDS:
                raise SchemaValidationException(f"{type_.name} is a reserved keyword")

            if isinstance(type_, GraphQLObjectType):
                if new_base_type not in type_.interfaces:
                    raise SchemaValidationException(f"Object type must implement base types [type={type_.name}]")
                if new_ooi_type not in type_.interfaces:
                    raise SchemaValidationException(f"Object type must implement base types [type={type_.name}]")

    def build_full_schema(self) -> GraphQLSchema:
        """Build the full schema.

        Combines all concrete types into a single union type.
        Defines the root query type, based on above union type.
        """
        # OOI Union = all object types that implement OOI
        object_types = [
            t
            for t in self.schema.type_map.values()
            if isinstance(t, GraphQLObjectType) and not t.name.startswith("__")
        ]
        ooi_union = GraphQLUnionType("UOOI", types=object_types)

        # Construct Query Type
        query = GraphQLObjectType("Query", fields={"OOI": GraphQLField(GraphQLList(ooi_union))})

        full_schema_kwargs = self.schema.to_kwargs()
        full_schema_kwargs["query"] = query
        full_schema_kwargs["types"] = full_schema_kwargs["types"] + (ooi_union, query)

        return GraphQLSchema(**full_schema_kwargs)


if __name__ == "__main__":
    schema_manager = SchemaManager.load_from_disk()
