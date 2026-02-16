"""Tests for the SSRF protection module."""

from __future__ import annotations

import socket as _socket
from unittest.mock import patch

import pytest

from apps.core.ssrf_protection import SSRFGuard


class TestSSRFGuard:
    """Test SSRF validation rejects dangerous URLs and allows safe ones."""

    def setup_method(self) -> None:
        self.guard = SSRFGuard()

    def test_allows_public_url(self) -> None:
        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            result = self.guard.validate_url("https://example.com")
        assert result.url == "https://example.com"
        assert result.resolved_ip == "93.184.216.34"

    def test_blocks_localhost_127(self) -> None:
        with (
            patch("socket.gethostbyname", return_value="127.0.0.1"),
            pytest.raises(ValueError, match="blocked IP range"),
        ):
            self.guard.validate_url("https://localhost")

    def test_blocks_private_10_network(self) -> None:
        with (
            patch("socket.gethostbyname", return_value="10.0.0.1"),
            pytest.raises(ValueError, match="blocked IP range"),
        ):
            self.guard.validate_url("https://internal.corp")

    def test_blocks_private_172_network(self) -> None:
        with (
            patch("socket.gethostbyname", return_value="172.16.0.1"),
            pytest.raises(ValueError, match="blocked IP range"),
        ):
            self.guard.validate_url("https://internal.corp")

    def test_blocks_private_192_network(self) -> None:
        with (
            patch("socket.gethostbyname", return_value="192.168.1.1"),
            pytest.raises(ValueError, match="blocked IP range"),
        ):
            self.guard.validate_url("https://home.local")

    def test_blocks_link_local(self) -> None:
        with (
            patch("socket.gethostbyname", return_value="169.254.169.254"),
            pytest.raises(ValueError, match="blocked IP range"),
        ):
            self.guard.validate_url("https://metadata.google.internal")

    def test_rejects_ftp_scheme(self) -> None:
        with pytest.raises(ValueError, match=r"scheme.*not allowed"):
            self.guard.validate_url("ftp://example.com/file.txt")

    def test_rejects_file_scheme(self) -> None:
        with pytest.raises(ValueError, match=r"scheme.*not allowed"):
            self.guard.validate_url("file:///etc/passwd")

    def test_rejects_no_hostname(self) -> None:
        with pytest.raises(ValueError, match="no hostname"):
            self.guard.validate_url("https://")

    def test_rejects_url_too_long(self) -> None:
        long_url = "https://example.com/" + "a" * 2048
        with pytest.raises(ValueError, match="maximum length"):
            self.guard.validate_url(long_url)

    def test_rejects_unresolvable_hostname(self) -> None:
        with (
            patch(
                "socket.gethostbyname",
                side_effect=_socket.gaierror("DNS failed"),
            ),
            pytest.raises(ValueError, match="Could not resolve"),
        ):
            self.guard.validate_url("https://nonexistent.invalid")

    def test_allows_http_scheme(self) -> None:
        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            result = self.guard.validate_url("http://example.com")
        assert result.url == "http://example.com"

    def test_allows_https_scheme(self) -> None:
        with patch("socket.gethostbyname", return_value="93.184.216.34"):
            result = self.guard.validate_url("https://example.com")
        assert result.url == "https://example.com"
