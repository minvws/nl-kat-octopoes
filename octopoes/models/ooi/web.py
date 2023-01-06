from abc import ABC
from datetime import datetime, timedelta, timezone
from enum import Enum
from http.cookies import SimpleCookie, CookieError
from typing import Literal, Optional, Iterator

from pydantic import AnyUrl

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.network import IPAddress, Network
from octopoes.models.ooi.service import IPService
from octopoes.models.persistence import ReferenceField


class Website(OOI):
    object_type: Literal["Website"] = "Website"

    ip_service: Reference = ReferenceField(IPService, max_issue_scan_level=0, max_inherit_scan_level=4)
    hostname: Reference = ReferenceField(Hostname, max_inherit_scan_level=4)

    _natural_key_attrs = ["ip_service", "hostname"]

    _reverse_relation_names = {"ip_service": "websites", "hostname": "websites"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        t = reference.tokenized
        service = t.ip_service.service.name
        addres = t.ip_service.ip_port.address.address
        port = t.ip_service.ip_port.port
        return f"{service}://{t.hostname.name}:{port} @ {addres}"


class WebScheme(Enum):
    HTTP = "http"
    HTTPS = "https"


class WebURL(OOI, ABC):
    network: Reference = ReferenceField(Network)

    scheme: WebScheme
    port: int
    path: str


class HostnameHTTPURL(WebURL):
    object_type: Literal["HostnameHTTPURL"] = "HostnameHTTPURL"

    netloc: Reference = ReferenceField(Hostname, max_issue_scan_level=2, max_inherit_scan_level=4)

    _natural_key_attrs = ["scheme", "netloc", "port", "path"]
    _reverse_relation_names = {"netloc": "urls"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        tokenized = reference.tokenized
        port = f":{tokenized.port}" if tokenized.port else ""
        return f"{tokenized.scheme}://{tokenized.netloc.name}{port}{tokenized.path}"


class IPAddressHTTPURL(WebURL):
    object_type: Literal["IPAddressHTTPURL"] = "IPAddressHTTPURL"

    netloc: Reference = ReferenceField(IPAddress, max_issue_scan_level=1, max_inherit_scan_level=4)

    _natural_key_attrs = ["scheme", "netloc", "port", "path"]
    _reverse_relation_names = {"netloc": "urls"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        tokenized = reference.tokenized
        port = f":{tokenized.port}" if tokenized.port else ""
        return f"{tokenized.scheme}://{tokenized.netloc.address}{port}{tokenized.path}"


class HTTPResource(OOI):
    object_type: Literal["HTTPResource"] = "HTTPResource"

    website: Reference = ReferenceField(Website, max_issue_scan_level=0, max_inherit_scan_level=4)
    web_url: Reference = ReferenceField(WebURL, max_issue_scan_level=1, max_inherit_scan_level=4)
    redirects_to: Optional[Reference] = ReferenceField(WebURL, default=None)

    _natural_key_attrs = ["website", "web_url"]

    _reverse_relation_names = {
        "website": "resources",
        "web_url": "resources",
    }

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        t = reference.tokenized
        port = f":{t.web_url.port}"
        try:
            netloc = t.web_url.netloc.address
        except KeyError:
            netloc = t.web_url.netloc.name

        web_url = f"{t.web_url.scheme}://{netloc}{port}{t.web_url.path}"
        address = t.website.ip_service.ip_port.address.address

        return f"{web_url} @ {address}"


class HTTPHeader(OOI):
    object_type: Literal["HTTPHeader"] = "HTTPHeader"

    resource: Reference = ReferenceField(HTTPResource, max_issue_scan_level=0, max_inherit_scan_level=4)
    key: str
    value: str

    _natural_key_attrs = ["resource", "key"]
    _information_value = ["key"]
    _reverse_relation_names = {"url": "http_headers"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        t = reference.tokenized

        port = f":{t.resource.web_url.port}" if t.resource.web_url.port else ""
        try:
            netloc = t.resource.web_url.netloc.address
        except KeyError:
            netloc = t.resource.web_url.netloc.name

        web_url = f"{t.resource.web_url.scheme}://{netloc}{port}{t.resource.web_url.path}"
        address = t.resource.website.ip_service.ip_port.address.address

        return f"{reference.tokenized.key} @ {web_url} @ {address}"


class URL(OOI):
    object_type: Literal["URL"] = "URL"

    network: Reference = ReferenceField(Network)
    raw: AnyUrl

    web_url: Optional[Reference] = ReferenceField(WebURL, max_issue_scan_level=2, default=None)

    _natural_key_attrs = ["network", "raw"]

    _reverse_relation_names = {"network": "urls"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        return f"{reference.tokenized.raw} @{reference.tokenized.network.name}"


class HTTPHeaderURL(OOI):
    object_type: Literal["HTTPHeaderURL"] = "HTTPHeaderURL"

    header: Reference = ReferenceField(HTTPHeader, max_issue_scan_level=0, max_inherit_scan_level=1)
    url: Reference = ReferenceField(URL, max_issue_scan_level=1, max_inherit_scan_level=0)

    _natural_key_attrs = ["header", "url"]
    _reverse_relation_names = {"header": "urls", "url": "headers_containing_url"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        t = reference.tokenized.header

        port = f":{t.resource.web_url.port}" if t.resource.web_url.port else ""
        try:
            netloc = t.resource.web_url.netloc.address
        except KeyError:
            netloc = t.resource.web_url.netloc.name

        web_url = f"{t.resource.web_url.scheme}://{netloc}{port}{t.resource.web_url.path}"
        address = t.resource.website.ip_service.ip_port.address.address

        return f"{t.key} @ {web_url} @ {address} contains {str(reference.tokenized.url.raw)}"


class HTTPHeaderHostname(OOI):
    object_type: Literal["HTTPHeaderHostname"] = "HTTPHeaderHostname"

    header: Reference = ReferenceField(HTTPHeader, max_issue_scan_level=0, max_inherit_scan_level=1)
    hostname: Reference = ReferenceField(Hostname, max_issue_scan_level=1, max_inherit_scan_level=0)

    _natural_key_attrs = ["header", "hostname"]
    _reverse_relation_names = {"header": "hostnames", "hostname": "headers_containing_hostname"}

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        t = reference.tokenized.header

        port = f":{t.resource.web_url.port}" if t.resource.web_url.port else ""
        try:
            netloc = t.resource.web_url.netloc.address
        except KeyError:
            netloc = t.resource.web_url.netloc.name

        web_url = f"{t.resource.web_url.scheme}://{netloc}{port}{t.resource.web_url.path}"
        address = t.resource.website.ip_service.ip_port.address.address

        return f"{t.key} @ {web_url} @ {address} contains {str(reference.tokenized.hostname.name)}"


class HTTPCookie(OOI):
    # https://datatracker.ietf.org/doc/html/rfc6265
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies
    object_type: Literal["HTTPCookie"] = "HTTPCookie"

    _natural_key_attrs = [
        "name",
        "domain",
        "path",
    ]  # does not include network, as there is not concept of a network only hostnames in the browsers cookie handling.

    # httpheader: Reference(ReferenceField(HTTPHeaderURL, max_inherit_scan_level=4))  # ideally we should keep track of
    # which header was parsed into this cookie object
    # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3
    name: str
    value: str
    expiry_time: Optional[datetime]
    # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p6
    domain: Reference = ReferenceField(Hostname, max_inherit_scan_level=4)
    # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p7
    path: str = "/"
    creation_time: datetime
    # last-access-time: # not used in openkat context
    # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p3
    persistent: bool = False
    # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p6
    host_only: bool = False
    # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p8
    secure_only: bool = False
    # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p9
    http_only: bool = False
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite
    same_site: bool = False
    max_age: Optional[int]

    @classmethod
    def format_reference_human_readable(cls, reference: Reference) -> str:
        tokenized = reference.tokenized
        return f"{tokenized.name} @ {tokenized.domain}"

    @classmethod
    def from_string(cls, response_domain, cookie) -> Iterator[OOI]:
        now = datetime.now(timezone.utc)

        # https://docs.python.org/3/library/http.cookies.html
        try:
            parsed_cookie = SimpleCookie(cookie)

            for name, morsel in parsed_cookie.items():
                # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p6
                host_only = False
                if not morsel["domain"]:
                    host_only = True
                    morsel["domain"] = response_domain

                # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p3
                persistent = False
                expires = float("inf")
                max_age = None
                if "max-age" in morsel:
                    persistent = True
                    try:
                        max_age = min(
                            1e8, int(morsel["max-age"])
                        )  # limit to make sure we dont trip over calculating a date millions of years in the future
                    except ValueError:
                        persistent = False
                    else:
                        expires = now + timedelta(max_age)

                elif morsel["expires"]:
                    persistent = True
                    expires = datetime.strptime(morsel["expires"])

                domain = Reference.from_str(morsel["domain"])  # load or create? todo: fix this
                yield HTTPCookie(
                    # httpheader=httpheader,
                    name=name,
                    value=morsel.value,
                    expiry_time=expires,
                    domain=domain,
                    path=morsel["path"] or "/",
                    creation_time=now,
                    persistent=persistent,
                    host_only=host_only,
                    secure_only=morsel["secure"],
                    http_only=morsel["httponly"],
                    same_site=morsel["samesite"],
                    max_age=max_age,
                )

        except CookieError as cookieerror:
            yield Finding(cookieerror)  # todo: fix this
