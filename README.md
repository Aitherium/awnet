# awnet

The **overlay/fabric layer** — which peers exist, and can I reach one?

```bash
pip install awnet
```

```python
from awnet import Registry, check_peer

reg = Registry("peers.json")
reg.add_peer("node1", ["node1.local:8080"])
reg.save()

result = check_peer("node1.local:8080")
if result.ok is True:
    print("peer is reachable")
elif result.ok is False:
    print("peer is known but unreachable")
else:  # ok is None
    print("could not determine")
```

```bash
awnet add peers.json node1 node1.local:8080
awnet check node1.local:8080        # 0 ok · 1 unreachable · 2 unknown
awnet list peers.json
awnet get peers.json node1
```

## What it actually does

Separates two distinct concerns:

1. **Registry**: which peers EXIST (their names and endpoints).
2. **Reachability**: whether I CAN REACH one right now.

**A peer that resolves is not a peer that is reachable.** DNS working does not
mean the service is listening. A hostname resolve today can be unreachable
tomorrow. A reachability cache is a thing that keeps saying "up" for days after
the peer is gone.

Three distinct states, reported as three different things:

| verdict | ok | meaning |
|---|---|---|
| `ok` | `True` | peer answers on the network |
| `unreachable` | `False` | peer exists (DNS works) but does not answer |
| `unknown` | `None` | we tried to check but could not determine |

Why this matters:

- `Unknown` means try again. The network is the issue, not the peer.
- `Unreachable` means the peer is gone. Update your route or failover.
- `True` means the peer is here. Use it.

Three outcomes that call for three different responses. A test that treats them
the same is a test that would pass whether the distinction is there or not.

## How it checks

1. **DNS resolution** — can I name the peer?
   - If DNS fails → unreachable (ok=False)
   - If DNS times out → unknown (ok=None)

2. **TCP connect** (if DNS succeeds) — is anything listening?
   - If connect succeeds → ok (ok=True)
   - If connect is refused → unreachable (ok=False)
   - If connect times out → unreachable (ok=False)
   - If connect errors → unknown (ok=None)

Socket is closed after each check (no resource leak).

## What it does not do — stated, not papered over

**This is NOT a VPN implementation.** It is the addressing and reachability
layer ABOVE one. You bring your own network; awnet tells you which peers are
there and whether you can reach them.

**A reachability check is a point-in-time snapshot.** A peer that answers at
check-time might be gone by the time you route to it. awnet returns what it
found; it does not promise that it will still be true when you use the result.

Conversely, **a peer marked unreachable five minutes ago might be back.** awnet
does NOT cache results. Every check is fresh. If you want caching, keep it
separate and ALWAYS expire it explicitly — a cache that forgets to expire is
more dangerous than no cache at all.

**TCP port 80 (HTTP) is the only probe.** awnet does not know about HTTPS,
gRPC, custom protocols, or anything else. If your peer listens on a different
port, awnet will reach it. If your peer only answers TLS and you probe plain
HTTP, awnet will report it unreachable (which is correct: plain HTTP is
unreachable on that peer). The separation is intentional — a fabric layer that
understands every protocol is a fabric layer that understands none of them.

## Tests

Every claim has a mutation that breaks it. Happy-path tests would let the
three-state distinction disappear into the code and break silently.

```bash
pip install -e ".[dev]" && pytest
```

A reachability check that doesn't assert the SPECIFIC state is one that would
pass whether the three values (True, False, None) are actually different or not.

## Design notes

- **No dependencies.** A fabric layer that needs an install before it can be
  read is one nobody reads during an incident. Only the stdlib.
- **Registry is separate from checks.** Knowing a peer exists is not the same as
  being able to reach it. Mixing them conflates two distinct questions.
- **Three-valued logic is the whole point.** "Unknown" is not "unreachable".
  The network is not the peer. A test that treats them the same is a test that
  has no teeth.
- **No caching in the library.** If you cache, you own expiry. A library that
  caches and forgets to expire is more dangerous than no library.

## Where it fits

Part of the `aw` family: [awgit](https://github.com/Aitherium/awgit) ·
[awgraph](https://github.com/Aitherium/awgraph) ·
[awseal](https://github.com/Aitherium/awseal) ·
[awdk](https://github.com/Aitherium/awdk) ·
[awdit](https://github.com/Aitherium/awdit) ·
[awnode](https://github.com/Aitherium/awnode)

Apache-2.0.
