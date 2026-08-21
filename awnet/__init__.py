"""awnet — peer registry and reachability layer.

A peer that resolves is not a peer that is reachable. A reachability cache is a
thing that keeps saying "up" after the peer is gone. Three distinct states
matter: unknown peer, known-but-unreachable peer, and unable-to-judge.

This is NOT a VPN implementation. It is the addressing and reachability layer
above one.
"""

from .check import CheckResult, check_peer
from .registry import Peer, PeerState, Registry

__all__ = [
    "Registry",
    "Peer",
    "PeerState",
    "check_peer",
    "CheckResult",
]
