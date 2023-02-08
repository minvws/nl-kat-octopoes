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
    GraphQLString,
    extend_schema,
    parse,
    GraphQLArgument,
    DocumentNode,
    DirectiveDefinitionNode,
    ObjectTypeDefinitionNode,
    TypeDefinitionNode,
    ScalarTypeDefinitionNode,
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


RESERVED_TYPE_NAMES = {
    "Query",
    "Mutation",
    "BaseObject",
    "OOI",
}


BASE_SCHEMA_FILE = Path(__file__).parent / "schemas" / "base_schema.graphql"
OOI_SCHEMA_FILE = Path(__file__).parent / "schemas" / "ooi_schema.graphql"
EXTENDED_SCHEMA_FILE = Path(__file__).parent / "schemas" / "extended_schema.graphql"


class BaseSchema:
    """Wrapper for a KAT GraphQLSchema that provides some convenience methods."""

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
            t
            for t in self.schema.type_map.values()
            if isinstance(t, GraphQLObjectType) and not t.name.startswith("__")
        ]

    @property
    def union_types(self) -> list[GraphQLUnionType]:
        """Return all union types."""
        return [
            t for t in self.schema.type_map.values() if isinstance(t, GraphQLUnionType) and not t.name.startswith("__")
        ]


class ExtendedSchema(BaseSchema):
    """Wrapper for a KAT GraphQLSchema with extended objects, like Origin and ScanProfile."""

    @property
    def ooi_union_type(self) -> GraphQLUnionType:
        """Return the OOI union type."""
        return cast(GraphQLUnionType, self.schema.type_map["UOOI"])

    @property
    def origin_type(self) -> GraphQLObjectType:
        """Return the Origin type."""
        return cast(GraphQLObjectType, self.schema.type_map["Origin"])

    @property
    def scan_profile_type(self) -> GraphQLObjectType:
        """Return the ScanProfile type."""
        return cast(GraphQLObjectType, self.schema.type_map["ScanProfile"])


class SchemaLoader:
    """Loads an OOI schema definition to validate and calculate derived schemas.

    Initialized with an OOI schema definition.
    Derived schemas:
    - base_schema: The base schema, which the OOI schema extends
    - ooi_schema: The OOI schema, which is validated
    - full_schema: The OOI schema, extended with KAT specific types
    - hydrated_schema: The full schema, where reverse fields are linked. Extended with Query type.
      Meant to expose to API
    """

    def __init__(self, ooi_schema_definition: Optional[str] = None):
        """Initialize instance."""
        self.ooi_schema_definition = (
            ooi_schema_definition if ooi_schema_definition is not None else OOI_SCHEMA_FILE.read_text()
        )
        self.validate_ooi_schema()

    @cached_property
    def base_schema(self) -> BaseSchema:
        """Return and cache the base schema."""
        return BaseSchema(build_schema(BASE_SCHEMA_FILE.read_text()))

    @cached_property
    def ooi_schema_document(self) -> DocumentNode:
        """Return and cache the parsed OOI schema."""
        return parse(self.ooi_schema_definition)

    @cached_property
    def ooi_schema(self) -> BaseSchema:
        """Load the schema from disk."""
        return BaseSchema(extend_schema(self.base_schema.schema, self.ooi_schema_document))

    def validate_ooi_schema(self) -> None:
        """Look into the AST of the schema definition file to apply restrictions.

        References:
            - https://graphql-core-3.readthedocs.io/en/latest/modules/language.html
        """
        # Check all definitions to apply validations
        for definition in self.ooi_schema_document.definitions:

            if isinstance(definition, DirectiveDefinitionNode):
                raise SchemaValidationException(
                    f"Custom directive definitions are not allowed [directive={definition.name.value}]"
                )

            if isinstance(definition, ScalarTypeDefinitionNode):
                raise SchemaValidationException(
                    f"Custom scalar definitions are not allowed [type={definition.name.value}]"
                )

            if isinstance(definition, TypeDefinitionNode):
                if definition.name.value in RESERVED_TYPE_NAMES:
                    raise SchemaValidationException(
                        f"Use of reserved type name is now allowed [type={definition.name.value}]"
                    )

            if isinstance(definition, ObjectTypeDefinitionNode):
                interface_names = [interface.name.value for interface in definition.interfaces]
                if "BaseObject" not in interface_names or "OOI" not in interface_names:
                    raise SchemaValidationException(
                        f"Object types must implement BaseObject and OOI [type={definition.name.value}]"
                    )

    @cached_property
    def extended_schema_document(self) -> DocumentNode:
        """Return and cache the base schema."""
        return parse(EXTENDED_SCHEMA_FILE.read_text())

    @cached_property
    def extended_schema(self) -> ExtendedSchema:
        """Build the extended schema.

        Combine all concrete types into a single union type.
        Load the extended schema.
        """
        # Create a new GraphQLSchema including OOI Union = all object types that implement OOI
        ooi_union = GraphQLUnionType("UOOI", types=self.ooi_schema.object_types)

        extended_schema_kwargs = self.ooi_schema.schema.to_kwargs()
        extended_schema_kwargs["types"] += (ooi_union,)

        extended_schema = extend_schema(GraphQLSchema(**extended_schema_kwargs), self.extended_schema_document)

        return ExtendedSchema(extended_schema)

    @cached_property
    def hydrated_schema(self) -> ExtendedSchema:
        """Build the hydrated schema.

        Add reverse fields to all object types.
        Add Query type.
        Add Mutation type.
        """
        # Create backlinks
        for type_ in self.extended_schema.object_types:
            for field_name, field in type_.fields.items():

                if getattr(field.type, "of_type", None) is None:
                    continue

                target_field_type = field.type.of_type

                if not isinstance(target_field_type, GraphQLObjectType):
                    continue

                if field.args.get("backlink", None):
                    continue

                target_field_type.fields[field.args["reverse_name"].default_value] = GraphQLField(
                    GraphQLList(type_), {"backlink": GraphQLArgument(GraphQLString, default_value=field_name)}
                )

        # Construct Query Type
        query_fields = {type_.name: GraphQLField(GraphQLList(type_)) for type_ in self.extended_schema.object_types}
        query_fields["OOI"] = GraphQLField(GraphQLList(self.extended_schema.ooi_union_type))
        query = GraphQLObjectType("Query", fields=query_fields)

        # Construct Mutation Type
        hydrated_schema_kwargs = self.extended_schema.schema.to_kwargs()
        hydrated_schema_kwargs["query"] = query
        hydrated_schema_kwargs["types"] = hydrated_schema_kwargs["types"] + (query,)

        return ExtendedSchema(GraphQLSchema(**hydrated_schema_kwargs))
