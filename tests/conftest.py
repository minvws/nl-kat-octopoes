from enum import Enum

import pytest

from octopoes.ddl.dataclasses import OOI


class Color(Enum):
    RED = "red"
    GREEN = "green"


class Animal(OOI):
    object_type = "Animal"
    name: str
    color: Color


Animal._natural_key_attrs = ["name"]
Animal._human_readable_format = "Hello: {name}"


class ZooKeeper(OOI):
    object_type = "ZooKeeper"
    name: str
    pet: Animal


ZooKeeper._natural_key_attrs = ["name"]
ZooKeeper._human_readable_format = "{name} pets {pet_name}"


@pytest.fixture
def animal():
    return Animal(name="Whiskers", color=Color.RED)


@pytest.fixture
def zookeeper(animal):
    return ZooKeeper(name="Leslie", pet=animal)
