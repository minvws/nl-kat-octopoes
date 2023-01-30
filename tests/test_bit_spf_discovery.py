from bits.spf_discovery.spf_discovery import run
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import DNSTXTRecord
from octopoes.models.ooi.email_security import DNSSPFRecord


def test_spf_discovery_simple_success():
    dnstxt_record = DNSTXTRecord(hostname=Reference.from_str("Hostname|internet|example.com."),
                                 value="v=spf1 ip4:1.1.1.1 ~all exp=explain._spf.example.com", )
    results = list(run(dnstxt_record, []))

    assert results[-1].dict() == DNSSPFRecord(
        dns_txt_record=dnstxt_record.reference,
        value="v=spf1 ip4:1.1.1.1 ~all exp=explain._spf.example.com",
        ttl=None,
        all="~",
        exp="explain._spf.example.com",
    ).dict()


def test_spf_discovery_invalid_():
    results = list(run(
        DNSTXTRecord(
            hostname=Reference.from_str("Hostname|internet|example.com."),
            value="v=spf1 asdasdasdas",
        ),
        []
    ))

    assert len(results) == 0

