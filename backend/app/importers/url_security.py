import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from urllib.parse import SplitResult, urlsplit, urlunsplit

from app.core.errors import ApplicationError

AddressResolver = Callable[[str, int], Awaitable[list[str]]]


async def _resolve_addresses(hostname: str, port: int) -> list[str]:
    def resolve() -> list[str]:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        return list({record[4][0] for record in records})

    try:
        return await asyncio.to_thread(resolve)
    except socket.gaierror as exception:
        raise ApplicationError(
            "The URL hostname could not be resolved.",
            code="url_resolution_failed",
            status_code=422,
        ) from exception


def _normalized_url(parts: SplitResult) -> str:
    hostname = parts.hostname or ""
    host = f"[{hostname}]" if ":" in hostname else hostname
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), host, path, parts.query, ""))


async def validate_public_url(
    url: str,
    *,
    resolver: AddressResolver = _resolve_addresses,
) -> str:
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError as exception:
        raise ApplicationError(
            "The URL is malformed.",
            code="invalid_url",
            status_code=422,
        ) from exception

    if parts.scheme.lower() not in {"http", "https"}:
        raise ApplicationError(
            "Only http and https URLs are allowed.",
            code="invalid_url_scheme",
            status_code=422,
        )
    if not parts.hostname:
        raise ApplicationError(
            "The URL must contain a hostname.",
            code="invalid_url",
            status_code=422,
        )
    if parts.username is not None or parts.password is not None:
        raise ApplicationError(
            "Credentials in URLs are not allowed.",
            code="url_credentials_forbidden",
            status_code=422,
        )

    effective_port = port or (443 if parts.scheme.lower() == "https" else 80)
    addresses = await resolver(parts.hostname, effective_port)
    if not addresses:
        raise ApplicationError(
            "The URL hostname did not resolve to an address.",
            code="url_resolution_failed",
            status_code=422,
        )

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ApplicationError(
                "URLs resolving to local, private, or reserved networks are blocked.",
                code="private_network_forbidden",
                status_code=422,
            )

    return _normalized_url(parts)

