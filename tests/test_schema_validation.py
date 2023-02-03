from pathlib import Path

import pytest

from octopoes.ddl.ddl import SchemaLoader, SchemaValidationException


def test_schema():
    SchemaLoader((Path(__file__).parent / "fixtures" / "schema_simple.graphql").read_text())


def test_schema__custom_scalar__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_custom_scalar.graphql").read_text())
        assert "Custom scalar are not allowed" in str(exc.value)


def test_schema__directive__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_directive.graphql").read_text())
        assert "Custom directives are not allowed" in str(exc.value)


def test_schema__reserved_type_name__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_reserved_type_name.graphql").read_text())
        assert "reserved type name" in str(exc.value)


def test_schema__no_interfaces_1__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_interfaces_1.graphql").read_text())
        assert "Object types must implement BaseObject and OOI" in str(exc.value)


def test_schema__no_interfaces_2__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_interfaces_2.graphql").read_text())
        assert "Object types must implement BaseObject and OOI" in str(exc.value)


def test_schema__no_interfaces_3__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_interfaces_3.graphql").read_text())
        assert "Object types must implement BaseObject and OOI" in str(exc.value)
