from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, Literal, Union

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddress
from octopoes.models.persistence import ReferenceField


class AlgorithmType(Enum):
    RSA = "RSA"
    ECC = "ECC"


class Certificate(OOI):
    object_type: Literal["Certificate"] = "Certificate"

    subject: str
    issuer: Optional[str]
    valid_from: str
    valid_until: str
    pk_algorithm: Optional[str]
    pk_size: Optional[int]
    pk_number: Optional[str]
    signed_by: Optional[Reference] = ReferenceField(
        "Certificate", max_issue_scan_level=1, max_inherit_scan_level=0, default=None
    )
    serial_number: str

    _natural_key_attrs = ["issuer", "serial_number"]

    @property
    def expired(self):
        return datetime.now() > datetime.fromisoformat(self.valid_until)

    _reverse_relation_names = {
        "signed_by": "signed_certificates",
    }

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"{reference.tokenized.issuer} ({reference.tokenized.serial_number})"


class SubjectAlternativeName(OOI):
    certificate: Reference = ReferenceField(Certificate)

    _natural_key_attrs = ["certificate"]


class SubjectAlternativeNameHostname(SubjectAlternativeName):
    object_type: Literal["SubjectAlternativeNameHostname"] = "SubjectAlternativeNameHostname"
    hostname: Reference = ReferenceField(Hostname, max_issue_scan_level=1, max_inherit_scan_level=0)

    _natural_key_attrs = SubjectAlternativeName._natural_key_attrs + ["hostname"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.hostname.name


class SubjectAlternativeNameIP(SubjectAlternativeName):
    object_type: Literal["SubjectAlternativeNameIP"] = "SubjectAlternativeNameIP"
    address: Reference = ReferenceField(IPAddress)

    _natural_key_attrs = SubjectAlternativeName._natural_key_attrs + ["address"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.address.address


class SubjectAlternativeNameQualifier(SubjectAlternativeName):
    object_type: Literal["SubjectAlternativeNameQualifier"] = "SubjectAlternativeNameQualifier"
    name: str

    _natural_key_attrs = SubjectAlternativeName._natural_key_attrs + ["name"]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return reference.tokenized.name


# todo: remove
class CertificateSubjectAlternativeName(OOI):
    object_type: Literal["CertificateSubjectAlternativeName"] = "CertificateSubjectAlternativeName"

    certificate: Reference = ReferenceField(Certificate, max_issue_scan_level=0, max_inherit_scan_level=1)
    hostname: Reference = ReferenceField(Hostname, max_issue_scan_level=1, max_inherit_scan_level=0)

    _natural_key_attrs = ["certificate", "hostname"]

    _reverse_relation_names = {"certificate": "subject_alternative_names", "hostname": "certificates"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return (
            f"{reference.tokenized.certificate.subject} ({reference.tokenized.certificate.issuer}) contains "
            + f"{reference.tokenized.hostname.name}"
        )


Certificate.update_forward_refs()
CertificateSubjectAlternativeName.update_forward_refs()  # todo: remove
SubjectAlternativeNameHostname.update_forward_refs()
SubjectAlternativeNameIP.update_forward_refs()
SubjectAlternativeNameQualifier.update_forward_refs()
