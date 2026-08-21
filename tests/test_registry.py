"""Registry tests — every claim, with mutations that break it.

The three-state distinction (unknown, unreachable, unknown_state) is the whole
point. A test that doesn't assert the SPECIFIC state is one that would pass
whether the distinction is there or not.
"""

import json

import pytest

from awnet import Peer, PeerState, Registry


def test_registry_starts_empty():
    """A new registry with no file is empty."""
    reg = Registry()
    assert reg.list_peers() == []
    assert reg.get_peer("nonexistent") is None


def test_add_and_get_peer():
    """Peers can be added and retrieved."""
    reg = Registry()
    reg.add_peer("node1", ["host1:8080", "host2:8080"])

    peer = reg.get_peer("node1")
    assert peer is not None
    assert peer.name == "node1"
    assert peer.endpoints == ["host1:8080", "host2:8080"]
    assert peer.state == PeerState.UNKNOWN


def test_add_updates_existing_peer():
    """Adding a peer that exists updates its endpoints."""
    reg = Registry()
    reg.add_peer("node1", ["old:8080"])
    reg.add_peer("node1", ["new:8080"])

    peer = reg.get_peer("node1")
    assert peer.endpoints == ["new:8080"]


def test_registry_persists_to_file(tmp_path):
    """Registry saves to and loads from JSON file."""
    filepath = tmp_path / "peers.json"

    # Write
    reg1 = Registry(filepath)
    reg1.add_peer("alpha", ["alpha.local:9000"])
    reg1.add_peer("beta", ["beta.local:9000"])
    reg1.save()

    # Read back
    reg2 = Registry(filepath)
    assert len(reg2.list_peers()) == 2

    alpha = reg2.get_peer("alpha")
    assert alpha.endpoints == ["alpha.local:9000"]

    beta = reg2.get_peer("beta")
    assert beta.endpoints == ["beta.local:9000"]


def test_registry_preserves_peer_state(tmp_path):
    """Peer state is persisted and loaded."""
    filepath = tmp_path / "peers.json"

    reg1 = Registry(filepath)
    peer = Peer("sentinel", ["sentinel:443"], state=PeerState.UNREACHABLE)
    reg1.peers["sentinel"] = peer
    reg1.save()

    # Load and verify state is preserved
    reg2 = Registry(filepath)
    loaded = reg2.get_peer("sentinel")
    assert loaded.state == PeerState.UNREACHABLE


def test_malformed_json_does_not_crash_on_load(tmp_path):
    """Loading a corrupted file returns an empty registry, not an error."""
    filepath = tmp_path / "bad.json"
    filepath.write_text("{not valid json}", encoding="utf-8")

    # This should NOT raise an exception; it should silently give an empty registry.
    reg = Registry(filepath)
    assert reg.list_peers() == []


def test_corrupt_state_value_reverts_to_unknown(tmp_path):
    """If a peer's state is an invalid enum value, it defaults to UNKNOWN."""
    filepath = tmp_path / "peers.json"
    filepath.write_text(
        json.dumps({
            "node1": {
                "endpoints": ["node1:8080"],
                "state": "invalid_state"
            }
        }),
        encoding="utf-8"
    )

    reg = Registry(filepath)
    peer = reg.get_peer("node1")
    assert peer.state == PeerState.UNKNOWN


def test_missing_file_gives_empty_registry(tmp_path):
    """Asking for a nonexistent file does not crash; it gives an empty registry."""
    filepath = tmp_path / "does_not_exist.json"

    reg = Registry(filepath)
    assert reg.list_peers() == []


def test_no_filepath_requires_save_target():
    """Calling save() without a filepath raises an error."""
    reg = Registry()
    reg.add_peer("node1", ["node1:8080"])

    with pytest.raises(ValueError, match="no filepath"):
        reg.save()


def test_file_created_on_first_save(tmp_path):
    """Saving to a new path creates the file."""
    filepath = tmp_path / "new_registry.json"
    assert not filepath.exists()

    reg = Registry(filepath)
    reg.add_peer("node1", ["node1:8080"])
    reg.save()

    assert filepath.exists()
    data = json.loads(filepath.read_text(encoding="utf-8"))
    assert "node1" in data


def test_three_states_are_distinct():
    """The three peer states are separate and matter."""
    unknown = PeerState.UNKNOWN
    unreachable = PeerState.UNREACHABLE
    unknown_state = PeerState.UNKNOWN_STATE

    assert unknown.value == "unknown"
    assert unreachable.value == "unreachable"
    assert unknown_state.value == "unknown_state"

    # The point: these are not interchangeable.
    assert unknown != unreachable
    assert unreachable != unknown_state
