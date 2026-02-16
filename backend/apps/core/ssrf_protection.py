"""SSRF protection: block requests to private/internal IP ranges."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import ClassVar
from urllib.parse import urlparse

from apps.core.models import ValidatedURL

logger = logging.getLogger(__name__)


class SSRFGuard:
    """Validates URLs to prevent Server-Side Request Forgery attacks.

    Resolves DNS and blocks any URL that resolves to a private or reserved IP range.
    """

    BLOCKED_NETWORKS: ClassVar[list[ipaddress.IPv4Network | ipaddress.IPv6Network]] = [
        ipaddress.IPv4Network("127.0.0.0/8"),
        ipaddress.IPv4Network("10.0.0.0/8"),
        ipaddress.IPv4Network("172.16.0.0/12"),
        ipaddress.IPv4Network("192.168.0.0/16"),
        ipaddress.IPv4Network("169.254.0.0/16"),
        ipaddress.IPv6Network("::1/128"),
        ipaddress.IPv6Network("fd00::/8"),
        ipaddress.IPv6Network("fe80::/10"),
    ]

    ALLOWED_SCHEMES: ClassVar[set[str]] = {"http", "https"}
    MAX_URL_LENGTH: ClassVar[int] = 2048

    def validate_url(self, url: str) -> ValidatedURL:
        """Validate a URL is safe to fetch (not SSRF).

        Raises ValueError if the URL is invalid or resolves to a blocked IP.
        """
        if len(url) > self.MAX_URL_LENGTH:
            msg = f"URL exceeds maximum length of {self.MAX_URL_LENGTH} characters"
            raise ValueError(msg)

        parsed = urlparse(url)

        if parsed.scheme not in self.ALLOWED_SCHEMES:
            msg = f"URL scheme '{parsed.scheme}' is not allowed. Use http or https."
            raise ValueError(msg)

        if not parsed.hostname:
            msg = "URL has no hostname"
            raise ValueError(msg)

        try:
            resolved_ip = socket.gethostbyname(parsed.hostname)
        except socket.gaierror as exc:
            msg = f"Could not resolve hostname '{parsed.hostname}'"
            raise ValueError(msg) from exc

        ip_addr = ipaddress.ip_address(resolved_ip)
        for network in self.BLOCKED_NETWORKS:
            if ip_addr in network:
                msg = f"URL resolves to blocked IP range ({network})"
                raise ValueError(msg)

        logger.debug("URL validated: %s -> %s", url, resolved_ip)
        return ValidatedURL(url=url, resolved_ip=resolved_ip)
