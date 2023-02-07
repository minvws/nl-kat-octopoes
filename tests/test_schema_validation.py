from pathlib import Path

import pytest

from octopoes.ddl.ddl import SchemaLoader, SchemaValidationException


# Complicated but valid schema (tests all of the above)
def test_schema():
    SchemaLoader((Path(__file__).parent / "fixtures" / "schema_sample.graphql").read_text())


def test_schema__natural_key_as_fields__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_incorrect_natural_key.graphql").read_text())
    assert str(exc.value) == "Natural keys must be defined as fields [type=Animal, natural_key=size]"


def test_schema__directive__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_directive.graphql").read_text())
    assert (
        str(exc.value) == "A schema may only define a Type, Enum, Union, or Interface, not Directive [directive=test]"
    )


def test_schema__constrained_types_no_scalar__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_custom_scalar.graphql").read_text())
    assert (
        str(exc.value) == "A schema may only define a Type, Enum, Union, or Interface, not Scalar [type=CustomScalar]"
    )


def test_schema__constrained_types_no_input__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_custom_input.graphql").read_text())
    assert str(exc.value) == "A schema may only define a Type, Enum, Union, or Interface, not Input [type=CatSpeech]"


def test_schema__reserved_type_name__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_reserved_type_name.graphql").read_text())
    assert str(exc.value) == "Use of reserved type name is not allowed [type=BaseObject]"


def test_schema__constrained_types_no_subscription__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_custom_subscription.graphql").read_text())
    assert str(exc.value) == "Use of reserved type name is not allowed [type=Subscription]"


def test_schema__constrained_types_no_query__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_custom_query.graphql").read_text())
    assert str(exc.value) == "Use of reserved type name is not allowed [type=Query]"


def test_schema__constrained_types_no_mutation__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_custom_mutation.graphql").read_text())
    assert str(exc.value) == "Use of reserved type name is not allowed [type=Mutation]"


def test_schema__no_inherit_baseobject__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_baseobject_inheritance.graphql").read_text())
    assert str(exc.value) == "An object must inherit both BaseObject and OOI (missing BaseObject) [type=Test]"


def test_schema__no_inherit_ooi__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_ooi_inheritance.graphql").read_text())
    assert str(exc.value) == "An object must inherit both BaseObject and OOI (missing OOI) [type=Test]"


def test_schema__no_inherit_baseobject_ooi__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_baseobject_ooi_inheritance.graphql").read_text())
    assert str(exc.value) == "An object must inherit both BaseObject and OOI (missing both) [type=Test]"


def test_schema__no_union_with_u__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_union_with_u.graphql").read_text())
    assert str(exc.value) == "Self-defined unions must start with a U [type=Animals]"


def test_schema__pascalcased_names__schemavalidationerror():
    with pytest.raises(SchemaValidationException) as exc:
        SchemaLoader((Path(__file__).parent / "fixtures" / "schema_no_pascalcase.graphql").read_text())
    assert str(exc.value) == "Object types must follow PascalCase conventions [type=zooKeeper]"
