from ipaddress import ip_address
import os
import socket

from backend.app.exceptions.handlers import ApiError


def endpoint_address(host: str, port: int, *, verified_tls: bool = True) -> str:
    if not host or not 1 <= port <= 65535:
        raise ApiError(422, "invalid_endpoint", "Enter a valid hostname and port")
    target = f"{host.lower()}:{port}"
    allowed = set(os.getenv("KG_SOURCE_ENDPOINTS", "").lower().replace(" ", "").split(","))
    development = set(os.getenv("KG_SOURCE_DEV_ENDPOINTS", "").lower().replace(" ", "").split(","))
    production = os.getenv("KG_DEPLOYMENT_ENV", "").lower() in {"prod", "production"}
    loopback = host.lower() in {"localhost", "127.0.0.1", "::1"}
    dev = not production and (loopback or target in development)
    if target not in allowed and not dev:
        raise ApiError(403, "source_endpoint_denied", "This endpoint is outside the configured source allowlist")
    if not verified_tls and not dev:
        raise ApiError(422, "source_tls_required", "Use certificate-verified TLS for this source")
    try:
        resolved = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        raise ApiError(422, "source_dns_failed", "The source hostname could not be resolved") from None
    addresses = [ip_address(result[4][0]) for result in resolved]
    for address in addresses:
        address = getattr(address, "ipv4_mapped", None) or address
        if (address.is_link_local or address.is_multicast or address.is_unspecified
                or (loopback and not address.is_loopback) or (not dev and address.is_loopback)):
            raise ApiError(403, "source_endpoint_denied", "The endpoint resolved to a prohibited address")
    if not addresses:
        raise ApiError(422, "source_dns_failed", "The source hostname could not be resolved")
    return str(min(addresses, key=lambda address: address.version))
