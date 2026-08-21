"""Reachability check tests — three outcomes with mutations that change them.

ok=True (reachable), ok=False (unreachable), ok=None (cannot determine) are
not interchangeable. Testing only the happy path would let bugs live here
forever because the distinction is invisible to a "test if it works" suite.
"""

import socket
from unittest.mock import MagicMock, patch

from awnet import check_peer


def test_reachable_peer_returns_ok_true():
    """A peer that answers returns ok=True."""
    with patch("socket.getaddrinfo"):
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket

            result = check_peer("example.com:8080")

            assert result.ok is True
            assert result.method == "tcp"
            assert result.error is None


def test_dns_failure_returns_ok_false():
    """If DNS fails, the peer is unknown (not reachable): ok=False."""
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.side_effect = socket.gaierror("Name or service not known")

        result = check_peer("nonexistent.invalid:8080")

        assert result.ok is False
        assert result.method == "dns"
        assert "DNS resolution failed" in result.error


def test_connection_refused_returns_ok_false():
    """Host exists but nothing is listening: ok=False."""
    with patch("socket.getaddrinfo"):
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect.side_effect = ConnectionRefusedError()
            mock_socket_class.return_value = mock_socket

            result = check_peer("localhost:9999")

            assert result.ok is False
            assert result.method == "tcp"
            assert "connection refused" in result.error


def test_connection_timeout_returns_ok_false():
    """Timeout trying to connect: the peer exists but is unreachable: ok=False."""
    with patch("socket.getaddrinfo"):
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect.side_effect = socket.timeout()
            mock_socket_class.return_value = mock_socket

            result = check_peer("slow.example.com:8080", timeout=0.5)

            assert result.ok is False
            assert result.method == "tcp"
            assert "timed out" in result.error


def test_dns_timeout_returns_ok_none():
    """DNS lookup times out: we cannot determine: ok=None."""
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.side_effect = socket.timeout()

        result = check_peer("example.com:8080")

        assert result.ok is None
        assert result.method == "dns"
        assert "timed out" in result.error


def test_dns_other_error_returns_ok_none():
    """An OSError during DNS (not gaierror, not timeout): we cannot determine: ok=None."""
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.side_effect = OSError("network is unreachable")

        result = check_peer("example.com:8080")

        assert result.ok is None
        assert result.method == "dns"
        assert "error" in result.error.lower()


def test_tcp_other_error_returns_ok_none():
    """An OSError during TCP connect (not ConnectionRefused, not timeout): ok=None."""
    with patch("socket.getaddrinfo"):
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect.side_effect = OSError("network is down")
            mock_socket_class.return_value = mock_socket

            result = check_peer("example.com:8080")

            assert result.ok is None
            assert result.method == "tcp"
            assert "error" in result.error.lower()


def test_default_port_is_80():
    """If no port is specified, default to 80."""
    with patch("socket.getaddrinfo"):
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket

            check_peer("example.com")

            # Verify that port 80 was used
            calls = mock_socket.connect.call_args_list
            assert len(calls) > 0
            assert calls[0][0][0][1] == 80


def test_invalid_port_returns_ok_none():
    """If port is not a number, we cannot determine: ok=None."""
    result = check_peer("example.com:notaport")

    assert result.ok is None
    assert result.method == "parse"
    assert "not a number" in result.error


def test_socket_is_closed_after_connect():
    """A successful connect closes the socket (no resource leak)."""
    with patch("socket.getaddrinfo"):
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket

            check_peer("example.com:8080")

            # Verify close was called
            mock_socket.close.assert_called_once()


def test_timeout_is_passed_to_socket():
    """The timeout parameter is passed to the socket."""
    with patch("socket.getaddrinfo"):
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket

            check_peer("example.com:8080", timeout=5.0)

            mock_socket.settimeout.assert_called_with(5.0)
