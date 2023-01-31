from pathlib import Path

import pytest

from octopoes.ddl.ddl import SchemaManager, SchemaValidationException

schema_manager = SchemaManager()


def test_schema():
    new_schema = schema_manager.load_schema(Path(__file__).parent / "fixtures" / "schema_simple.graphql")
    schema_manager.validate(new_schema)


def test_schema__custom_scalar__schemavalidationerror():
    new_schema = schema_manager.load_schema(Path(__file__).parent / "fixtures" / "schema_custom_scalar.graphql")
    with pytest.raises(SchemaValidationException) as _:
        schema_manager.validate(new_schema)


def test_schema__reserved_keywords__schemavalidationerror():
    new_schema = schema_manager.load_schema(Path(__file__).parent / "fixtures" / "schema_reserved_keywords.graphql")
    with pytest.raises(SchemaValidationException) as _:
        schema_manager.validate(new_schema)


def test_schema__no_interfaces_1__schemavalidationerror():
    new_schema = schema_manager.load_schema(Path(__file__).parent / "fixtures" / "schema_no_interfaces_1.graphql")
    with pytest.raises(SchemaValidationException) as _:
        schema_manager.validate(new_schema)


def test_schema__no_interfaces_2__schemavalidationerror():
    new_schema = schema_manager.load_schema(Path(__file__).parent / "fixtures" / "schema_no_interfaces_2.graphql")
    with pytest.raises(SchemaValidationException) as _:
        schema_manager.validate(new_schema)


def test_schema__no_interfaces_3__schemavalidationerror():
    new_schema = schema_manager.load_schema(Path(__file__).parent / "fixtures" / "schema_no_interfaces_3.graphql")
    with pytest.raises(SchemaValidationException) as _:
        schema_manager.validate(new_schema)


def test_schema__directive__schemavalidationerror():
    new_schema = schema_manager.load_schema(Path(__file__).parent / "fixtures" / "schema_directive.graphql")
    with pytest.raises(SchemaValidationException) as _:
        schema_manager.validate(new_schema)
