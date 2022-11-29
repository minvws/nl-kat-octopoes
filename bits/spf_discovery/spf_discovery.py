from typing import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSTXTRecord
from octopoes.models.ooi.email_security import DNSSPFRecord


def run(
    input_ooi: DNSTXTRecord,
    additional_oois,
) -> Iterator[OOI]:

    if input_ooi.value.startswith("v=spf1"):
        yield DNSSPFRecord(
            dns_txt_record=input_ooi.reference,
            value=input_ooi.value,
            ttl=input_ooi.ttl)
