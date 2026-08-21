"""Check whether a peer is reachable.

This is separated from the registry on purpose. Knowing a peer exists (registry)
is not the same as being able to reach it (check). Mixing them conflates two
distinct questions and turns a reachability cache into an answer that STILL says
"up" after the peer is gone.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Optional


@dataclass
class CheckResult:
    """Result of a reachability check.

    `ok`: True if the peer answers, False if unreachable, None if could not
    determine. The three-valued logic matters: "I don't know" is not the same as
    "it doesn't answer".

    `method`: how we checked (DNS resolve, TCP connect, HTTP probe, etc).

    `error`: if not ok, what went wrong. If ok is None, error explains why we
    could not check.
    """
    ok: Optional[bool]
    method: str
    error: Optional[str] = None


def check_peer(endpoint: str, timeout: float = 2.0) -> CheckResult:
    """Check whether a peer endpoint is reachable.

    Tries DNS resolution first. If that fails, the peer is unknown (not
    reachable — there is no peer to reach). If DNS succeeds, tries TCP connect.

    Returns three states:
    - ok=True: endpoint answers on the network
    - ok=False: endpoint is known but does not answer
    - ok=None: we could not determine (timeout, I/O error, etc.)
    """
    # Parse endpoint. Format: "host:port" or just "host" (assume 80).
    parts = endpoint.rsplit(":", 1)
    if len(parts) == 2:
        host, port_str = parts
        try:
            port = int(port_str)
        except ValueError:
            return CheckResult(
                ok=None,
                method="parse",
                error=f"port is not a number: {port_str!r}"
            )
    else:
        host = parts[0]
        port = 80

    # Step 1: DNS resolution.
    try:
        socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        # DNS failed. Peer is unknown (not reachable — there is no address).
        return CheckResult(
            ok=False,
            method="dns",
            error=f"DNS resolution failed: {e}"
        )
    except socket.timeout:
        return CheckResult(
            ok=None,
            method="dns",
            error="DNS resolution timed out"
        )
    except OSError as e:
        # Some other network error during DNS. We don't know.
        return CheckResult(
            ok=None,
            method="dns",
            error=f"DNS error: {e}"
        )

    # Step 2: TCP connect (proof that something is listening).
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return CheckResult(ok=True, method="tcp")
    except socket.timeout:
        # Could not connect in time. The peer exists (DNS worked) but is
        # unreachable or too slow.
        return CheckResult(
            ok=False,
            method="tcp",
            error="connection timed out"
        )
    except ConnectionRefusedError:
        # Host is known, port is not listening. Unreachable.
        return CheckResult(
            ok=False,
            method="tcp",
            error="connection refused"
        )
    except OSError as e:
        # Some other network error. We don't know if the peer is up.
        return CheckResult(
            ok=None,
            method="tcp",
            error=f"connection error: {e}"
        )
