"""GraphQL DDL module."""
from __future__ import annotations

import re
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
    GraphQLNonNull,
    DocumentNode,
    DirectiveDefinitionNode,
    ObjectTypeDefinitionNode,
    TypeDefinitionNode,
    ScalarTypeDefinitionNode,
    InputObjectTypeDefinitionNode,
    UnionTypeDefinitionNode,
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
    "Subscription",
    "BaseObject",
    "OOI",
}


BASE_SCHEMA_FILE = Path(__file__).parent / "schemas" / "base_schema.graphql"
OOI_SCHEMA_FILE = Path(__file__).parent / "schemas" / "ooi_schema.graphql"


class OOISchema:
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


class HydratedSchema(OOISchema):
    """Wrapper for a KAT GraphQLSchema with reverse fields linked, and Query type added."""

    @property
    def ooi_union_type(self) -> GraphQLUnionType:
        """Return the OOI union type."""
        return cast(GraphQLUnionType, self.schema.type_map["UOOI"])


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
    def base_schema(self) -> OOISchema:
        """Return and cache the base schema."""
        return OOISchema(build_schema(BASE_SCHEMA_FILE.read_text()))

    @cached_property
    def ooi_schema_document(self) -> DocumentNode:
        """Return and cache the parsed OOI schema."""
        return parse(self.ooi_schema_definition)

    @cached_property
    def ooi_schema(self) -> OOISchema:
        """Load the schema from disk."""
        return OOISchema(extend_schema(self.base_schema.schema, self.ooi_schema_document))

    def validate_ooi_schema(self) -> None:
        """Look into the AST of the schema definition file to apply restrictions.

        References:
            - https://graphql-core-3.readthedocs.io/en/latest/modules/language.html
        """
        # Check all definitions to apply validations
        for definition in self.ooi_schema_document.definitions:

            if isinstance(definition, DirectiveDefinitionNode):
                raise SchemaValidationException(
                    f"A schema may only define a Type, Enum, Union, or Interface, not Directive "
                    f"[directive={definition.name.value}]"
                )

            if isinstance(definition, InputObjectTypeDefinitionNode):
                raise SchemaValidationException(
                    f"A schema may only define a Type, Enum, Union, or Interface, not Input "
                    f"[type={definition.name.value}]"
                )

            if isinstance(definition, ScalarTypeDefinitionNode):
                raise SchemaValidationException(
                    f"A schema may only define a Type, Enum, Union, or Interface, not Scalar "
                    f"[type={definition.name.value}]"
                )

            if isinstance(definition, UnionTypeDefinitionNode) and not definition.name.value.startswith("U"):
                raise SchemaValidationException(
                    f"Self-defined unions must start with a U [type={definition.name.value}]"
                )

            if isinstance(definition, TypeDefinitionNode):
                if definition.name.value in RESERVED_TYPE_NAMES or definition.name.value in BUILTIN_TYPES:
                    raise SchemaValidationException(
                        f"Use of reserved type name is not allowed [type={definition.name.value}]"
                    )

            if not re.match(r"^[A-Z][a-z]+(?:[A-Z][a-z]+)*$", definition.name.value):
                raise SchemaValidationException(
                    f"Object types must follow PascalCase conventions [type={definition.name.value}]"
                )

            if isinstance(definition, ObjectTypeDefinitionNode):
                interface_names = [interface.name.value for interface in definition.interfaces]
                if "BaseObject" not in interface_names and "OOI" not in interface_names:
                    raise SchemaValidationException(
                        f"An object must inherit both BaseObject and OOI (missing both) "
                        f"[type={definition.name.value}]"
                    )
                if "BaseObject" not in interface_names and "OOI" in interface_names:
                    raise SchemaValidationException(
                        f"An object must inherit both BaseObject and OOI (missing BaseObject) "
                        f"[type={definition.name.value}]"
                    )
                if "BaseObject" in interface_names and "OOI" not in interface_names:
                    raise SchemaValidationException(
                        f"An object must inherit both BaseObject and OOI (missing OOI) "
                        f"[type={definition.name.value}]"
                    )

    @cached_property
    def full_schema(self) -> OOISchema:
        """Build the full schema.

        Combines all concrete types into a single union type.
        Defines the root query type, based on above union type.
        """
        # OOI Union = all object types that implement OOI
        ooi_union = GraphQLUnionType("UOOI", types=self.ooi_schema.object_types)

        # Construct Scan Profile Type
        scan_level = GraphQLEnumType("ScanLevel", values={"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4})
        scan_profile_type = GraphQLEnumType(
            "ScanProfileType", values={"empty": "empty", "declared": "declared", "inherited": "inherited"}
        )
        scan_profile = GraphQLObjectType(
            "ScanProfile",
            fields={
                "object_type": GraphQLField(GraphQLNonNull(GraphQLString)),
                "primary_key": GraphQLField(
                    GraphQLNonNull(
                        GraphQLID,
                    ),
                    args={"natural_key": GraphQLArgument(GraphQLList(GraphQLString), default_value=["ooi"])},
                ),
                "human_readable": GraphQLField(
                    GraphQLNonNull(GraphQLString), args={"format": GraphQLArgument(GraphQLString, default_value="")}
                ),
                "type": GraphQLField(scan_profile_type),
                "level": GraphQLField(scan_level),
                "ooi": GraphQLField(ooi_union),
            },
            interfaces=[self.ooi_schema.base_object_type],
        )

        full_schema_kwargs = self.ooi_schema.schema.to_kwargs()
        full_schema_kwargs["types"] = full_schema_kwargs["types"] + (ooi_union, scan_profile)

        return OOISchema(GraphQLSchema(**full_schema_kwargs))

    @cached_property
    def hydrated_schema(self) -> HydratedSchema:
        """Build the hydrated schema."""
        # Construct Query Type
        ooi_union = self.full_schema.schema.type_map["UOOI"]
        query = GraphQLObjectType("Query", fields={"OOI": GraphQLField(GraphQLList(ooi_union))})

        hydrated_schema_kwargs = self.full_schema.schema.to_kwargs()
        hydrated_schema_kwargs["query"] = query
        hydrated_schema_kwargs["types"] = hydrated_schema_kwargs["types"] + (query,)

        return HydratedSchema(GraphQLSchema(**hydrated_schema_kwargs))
