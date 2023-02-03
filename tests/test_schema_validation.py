from pathlib import Path

import pytest

from octopoes.ddl.ddl import SchemaLoader, SchemaValidationException


def test_schema():
    SchemaLoader((Path(__file__).parent / "fixtures" / "schema_sample.graphql").read_text())


def test_schema__custom_scalar__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_custom_scalar.graphql").read_text())
    assert str(exc.value) == "Custom scalar definitions are not allowed [type=CustomScalar]"


def test_schema__directive__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_directive.graphql").read_text())
    assert str(exc.value) == "Custom directive definitions are not allowed [directive=test]"


def test_schema__reserved_type_name__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_reserved_type_name.graphql").read_text())
    assert str(exc.value) == "Use of reserved type name is now allowed [type=BaseObject]"


def test_schema__no_interfaces_1__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_interfaces_1.graphql").read_text())
    assert str(exc.value) == "Object types must implement BaseObject and OOI [type=Test]"


def test_schema__no_interfaces_2__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_interfaces_2.graphql").read_text())
    assert str(exc.value) == "Object types must implement BaseObject and OOI [type=Test]"


def test_schema__no_interfaces_3__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_interfaces_3.graphql").read_text())
    assert str(exc.value) == "Object types must implement BaseObject and OOI [type=Test]"
