"""Peer registry — which peers exist and how to reach them.

A peer is known, but knowing it exists does NOT mean it is reachable. Keeping
these states separate is the design. A hostname resolves today and is unreachable
tomorrow; the cache is a thing that answers "up" for days after the peer is gone.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class PeerState(Enum):
    """Three states, not two.

    UNKNOWN: we have never heard of this peer.
    UNREACHABLE: we know it exists but cannot reach it.
    UNKNOWN_STATE: we tried to check but could not determine if it is reachable.
    """
    UNKNOWN = "unknown"
    UNREACHABLE = "unreachable"
    UNKNOWN_STATE = "unknown_state"


@dataclass
class Peer:
    """A peer in the fabric.

    `name` is the identifier. `endpoints` are where it might be reached
    (hostnames, IPs, paths). `state` reflects the last check, not the hostname
    resolution. A peer whose DNS resolves to "up" is still unreachable if the
    service is not answering.
    """
    name: str
    endpoints: list[str]
    state: PeerState = PeerState.UNKNOWN
    last_check_error: Optional[str] = None


class Registry:
    """A registry of peers and their reachability.

    Registry does NOT check peers — it HOLDS them. Checking is separate
    (check_peer function) so the two concerns do not mix. This keeps the registry
    dumb and fast; reachability checks are I/O-bound and should be cached
    separately, never baked into the registry.
    """

    def __init__(self, filepath: Optional[Path | str] = None):
        """Initialize registry, optionally from a file.

        The file holds JSON. An unreadable or missing file is not an error here
        — that is the caller's problem. The registry stores NOTHING that changes:
        only peer NAMES and their ENDPOINTS, not reachability state (state is
        transient and must be checked fresh).
        """
        self.filepath = Path(filepath) if filepath else None
        self.peers: dict[str, Peer] = {}

        if self.filepath and self.filepath.is_file():
            data = None
            try:
                data = json.loads(self.filepath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, KeyError):
                # File exists but is corrupt. The caller gets an empty registry.
                # This is intentional — the caller should verify it if needed.
                data = None

            if data:
                for peer_name, peer_data in data.items():
                    # Read the stored state only to preserve intent; real state
                    # requires a live check.
                    endpoints = peer_data.get("endpoints", [])
                    stored_state = peer_data.get("state", "unknown")
                    try:
                        state = PeerState(stored_state)
                    except ValueError:
                        state = PeerState.UNKNOWN

                    self.peers[peer_name] = Peer(
                        name=peer_name,
                        endpoints=endpoints,
                        state=state,
                    )

    def add_peer(self, name: str, endpoints: list[str]) -> None:
        """Register a new peer or update its endpoints."""
        if name in self.peers:
            self.peers[name].endpoints = endpoints
        else:
            self.peers[name] = Peer(name=name, endpoints=endpoints)

    def get_peer(self, name: str) -> Optional[Peer]:
        """Retrieve a peer by name."""
        return self.peers.get(name)

    def list_peers(self) -> list[Peer]:
        """Return all registered peers."""
        return list(self.peers.values())

    def save(self) -> None:
        """Write registry to the file."""
        if not self.filepath:
            raise ValueError("no filepath configured for this registry")

        data = {}
        for peer in self.peers.values():
            data[peer.name] = {
                "endpoints": peer.endpoints,
                "state": peer.state.value,
            }

        self.filepath.write_text(
            json.dumps(data, indent=2, sort_keys=True),
            encoding="utf-8"
        )
