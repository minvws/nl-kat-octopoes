from __future__ import annotations

import json
from enum import Enum
from typing import Dict, Optional, Literal, Union, List

import pydantic
from pydantic import BaseModel


class PrimitiveFieldType(Enum):
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"


class FieldType(Enum):
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    ENUM = "enum"


class FieldDefinition(BaseModel):
    type: Union[FieldType, str]
    multiple: bool = False

    class Config:
        use_enum_values = True


class EnumFieldDefinition(FieldDefinition):
    type: Literal[FieldType.ENUM] = FieldType.ENUM
    members: Dict[str, str]


FIELD_DEFINITION_TYPES = Union[FieldDefinition, EnumFieldDefinition]


class ClassDefinition(BaseModel):
    name: str
    version: str
    abstract: bool = False
    parent: Optional[str] = None
    fields: Dict[str, Union[PrimitiveFieldType, str, FIELD_DEFINITION_TYPES]]
    natural_key: Optional[List[str]]

    class Config:
        use_enum_values = True


class SchemaDefinition(BaseModel):
    module: str
    classes: List[ClassDefinition]


class HydratedClassDefinition(ClassDefinition):
    parent: Optional[HydratedClassDefinition] = None


HydratedClassDefinition.update_forward_refs()


class SchemaManager:
    def __init__(self, definition: SchemaDefinition):
        self.definition = definition
        self.cls_defs = {f"{definition.module}_{cls.name}_{cls.version}": cls for cls in definition.classes}
        self.hydrated_cls_defs: Dict[str, HydratedClassDefinition] = {}

        self.hydrate_parents()

    def hydrate_parents(self):

        # convert cls_defs to hydrated
        for cls_ in self.cls_defs.values():
            data = cls_.dict()
            data.pop("parent")
            self.hydrated_cls_defs[f"{self.definition.module}_{cls_.name}_{cls_.version}"] = HydratedClassDefinition(
                **data
            )

        # hydrate parents
        for cls_id, cls in self.hydrated_cls_defs.items():
            if self.cls_defs[cls_id].parent:
                cls.parent = self.hydrated_cls_defs[self.cls_defs[cls_id].parent]

    @staticmethod
    def calc_inherited(class_definition: HydratedClassDefinition) -> Dict[str, FieldDefinition]:
        # TODO: implement
        fields = class_definition.fields.copy()
        if class_definition.parent:
            parent_fields = SchemaManager.calc_inherited(class_definition.parent)
            class_definition.fields.update(class_definition.parent.fields)
        else:
            return {}


if __name__ == "__main__":

    # first cmd-line arg is the yaml ddl
    import sys
    import yaml

    with open(sys.argv[1]) as f:
        ddl = yaml.safe_load(f)

        # parse the ddl
        class_def = SchemaDefinition.parse_obj(ddl)

        # print the ddl
        print(json.dumps(class_def.dict(), indent=4))

        schema_loader = SchemaManager(class_def)
        schema_loader.hydrate_parents()
