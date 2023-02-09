from pathlib import Path

import pytest

from octopoes.ddl.ddl import SchemaLoader, SchemaValidationException


def schema_validation(schema: str, expected_output: str) -> bool:
    """Helper function for testing schema validation."""
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / schema).read_text())
    if str(exc.value) in expected_output:
        return True

    return False


# Complicated but valid schema (tests all of the above)
def test_schema():
    SchemaLoader((Path(__file__).parent / "fixtures" / "schema_sample.graphql").read_text())


def test_schema__natural_key_as_fields__schemavalidationerror():
    assert schema_validation(
        "schema_incorrect_natural_key.graphql",
        "Natural keys must be defined as fields [type=Animal, natural_key=size]",
    )


def test_schema__directive__schemavalidationerror():
    assert schema_validation(
        "schema_directive.graphql",
        "A schema may only define a Type, Enum, Union, or Interface, not Directive [directive=test]",
    )


def test_schema__constrained_types_no_scalar__schemavalidationerror():
    assert schema_validation(
        "schema_custom_scalar.graphql",
        "A schema may only define a Type, Enum, Union, or Interface, not Scalar [type=CustomScalar]",
    )


def test_schema__constrained_types_no_input__schemavalidationerror():
    assert schema_validation(
        "schema_custom_input.graphql",
        "A schema may only define a Type, Enum, Union, or Interface, not Input [type=CatSpeech]",
    )


def test_schema__reserved_type_name__schemavalidationerror():
    assert schema_validation(
        "schema_reserved_type_name.graphql", "Use of reserved type name is not allowed [type=BaseObject]"
    )


def test_schema__constrained_types_no_subscription__schemavalidationerror():
    assert schema_validation(
        "schema_custom_subscription.graphql", "Use of reserved type name is not allowed [type=Subscription]"
    )


def test_schema__constrained_types_no_query__schemavalidationerror():
    assert schema_validation("schema_custom_query.graphql", "Use of reserved type name is not allowed [type=Query]")


def test_schema__constrained_types_no_mutation__schemavalidationerror():
    assert schema_validation(
        "schema_custom_mutation.graphql", "Use of reserved type name is not allowed [type=Mutation]"
    )


def test_schema__no_inherit_baseobject__schemavalidationerror():
    assert schema_validation(
        "schema_no_baseobject_inheritance.graphql",
        "An object must inherit both BaseObject and OOI (missing BaseObject) [type=Test]",
    )


def test_schema__no_inherit_ooi__schemavalidationerror():
    assert schema_validation(
        "schema_no_ooi_inheritance.graphql", "An object must inherit both BaseObject and OOI (missing OOI) [type=Test]"
    )


def test_schema__no_inherit_baseobject_ooi__schemavalidationerror():
    assert schema_validation(
        "schema_no_baseobject_ooi_inheritance.graphql",
        "An object must inherit both BaseObject and OOI (missing both) [type=Test]",
    )


def test_schema__no_union_with_u__schemavalidationerror():
    assert schema_validation(
        "schema_no_union_with_u.graphql", "Self-defined unions must start with a U [type=Animals]"
    )


def test_schema__pascalcased_names__schemavalidationerror():
    assert schema_validation(
        "schema_no_pascalcase.graphql", "Object types must follow PascalCase conventions [type=zooKeeper]"
    )
