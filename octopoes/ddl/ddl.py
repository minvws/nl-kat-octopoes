from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import cast

from graphql import (
    build_schema,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLSchema,
    print_type,
    specified_directives,
)


logger = getLogger(__name__)


class SchemaValidationException(Exception):
    pass


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

RESERVED_KEYWORDS = {
    "Query",
    "Mutation",
}


class SchemaManager:
    def __init__(self):
        self.base_schema = self.load_schema(path=Path(__file__).parent / "schemas" / "base_schema.graphql")

        self.ooi_type = cast(GraphQLInterfaceType, self.base_schema.type_map["BaseOOI"])
        self.base_type = cast(GraphQLInterfaceType, self.base_schema.type_map["BaseObject"])

        self.current_schema = self.base_schema

    @staticmethod
    def load_schema(path: Path) -> GraphQLSchema:
        with open(path) as f:
            schema = build_schema(f.read())
            logger.info("Loaded schema: %s", path)
            return schema

    def validate(self, new_schema: GraphQLSchema) -> None:

        # Validate root types
        if "BaseOOI" not in new_schema.type_map:
            raise SchemaValidationException("Schema must contain OOI interface")

        if "BaseObject" not in new_schema.type_map:
            raise SchemaValidationException("Schema must contain BaseObject interface")

        new_ooi_type = cast(GraphQLInterfaceType, new_schema.type_map["BaseOOI"])
        new_base_type = cast(GraphQLInterfaceType, new_schema.type_map["BaseObject"])

        if print_type(new_ooi_type) != print_type(self.ooi_type):
            raise SchemaValidationException(f"{self.ooi_type.name} must equal orginal type")

        if print_type(new_base_type) != print_type(self.base_type):
            raise SchemaValidationException(f"{self.base_type.name} must equal orginal type")

        # Validate directives, no custom directives are allowed
        directive_names = {d.name for d in new_schema.directives}
        if directive_names - BUILTIN_DIRECTIVES:
            raise SchemaValidationException("Custom directives are not allowed")

        # Validate object types
        for type_ in new_schema.type_map.values():
            if type_.name in BUILTIN_TYPES:
                continue

            if type_ == new_ooi_type or type_ == new_base_type:
                continue

            if type_.name in RESERVED_KEYWORDS:
                raise SchemaValidationException(f"{type_.name} is a reserved keyword")

            if not isinstance(type_, GraphQLObjectType):
                raise SchemaValidationException(f"Type {type_.name} must be an object type")

            if new_base_type not in type_.interfaces:
                raise SchemaValidationException(f"Object type must implement base types [type={type_.name}]")
            if new_ooi_type not in type_.interfaces:
                raise SchemaValidationException(f"Object type must implement base types [type={type_.name}]")


if __name__ == "__main__":
    schema_manager = SchemaManager()
    print(Path(__file__).parent / "schemas" / "openkat_schema.graphql")
    new_schema_ = schema_manager.load_schema(Path(__file__).parent / "schemas" / "openkat_schema.graphql")
    schema_manager.validate(new_schema_)
