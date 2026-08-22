"""awnet CLI.

Exit codes are the contract:
  0: success (healthy peer, registry loaded/saved, etc.)
  1: a real problem (peer unreachable, malformed registry, etc.)
  2: could not judge (I/O error, timeout, missing file, etc.)

The three-valued logic is load-bearing: "we don't know" is not the same as
"it doesn't work", and treating them the same is how a stale cache turns into
a false assurance.
"""

from __future__ import annotations

import argparse
import json
import sys

from .check import check_peer
from .registry import Registry


def main(argv: list[str] | None = None) -> int:
    # GENERATED doctor intercept (gen_aw_doctor.py) -- do not edit
    _dv = locals().get("argv")
    if (_dv if _dv is not None else __import__("sys").argv[1:])[:1] == ["doctor"]:
        from ._doctor import report
        return report()
    ap = argparse.ArgumentParser(
        prog="awnet",
        description="Peer registry and reachability layer"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # Subcommand: add a peer
    add_cmd = sub.add_parser("add", help="register a peer")
    add_cmd.add_argument("registry")
    add_cmd.add_argument("peer_name")
    add_cmd.add_argument("endpoints", nargs="+", help="endpoints (host:port)")

    # Subcommand: check reachability
    check_cmd = sub.add_parser("check", help="check if a peer is reachable")
    check_cmd.add_argument("endpoint")
    check_cmd.add_argument("--timeout", type=float, default=2.0)
    check_cmd.add_argument("--json", action="store_true")

    # Subcommand: list peers
    list_cmd = sub.add_parser("list", help="list registered peers")
    list_cmd.add_argument("registry")

    # Subcommand: get peer info
    get_cmd = sub.add_parser("get", help="get peer details")
    get_cmd.add_argument("registry")
    get_cmd.add_argument("peer_name")

    args = ap.parse_args(argv)

    # ADD: register a peer
    if args.cmd == "add":
        try:
            registry = Registry(args.registry)
        except Exception as e:
            print(f"DEAD: could not load registry: {e}", file=sys.stderr)
            return 2

        registry.add_peer(args.peer_name, args.endpoints)
        try:
            registry.save()
        except Exception as e:
            print(f"ERROR: could not save registry: {e}", file=sys.stderr)
            return 1

        print(f"added {args.peer_name} with {len(args.endpoints)} endpoint(s)")
        return 0

    # CHECK: reachability
    if args.cmd == "check":
        result = check_peer(args.endpoint, timeout=args.timeout)

        if args.json:
            print(json.dumps({
                "ok": result.ok,
                "method": result.method,
                "error": result.error
            }))
        else:
            if result.ok is True:
                print(f"ok: {args.endpoint} is reachable (checked via {result.method})")
            elif result.ok is False:
                print(f"unreachable: {args.endpoint} — {result.error}")
            else:  # ok is None
                print(f"unknown: could not check {args.endpoint} — {result.error}")

        if result.ok is True:
            return 0
        elif result.ok is False:
            return 1
        else:  # None
            return 2

    # LIST: show all peers
    if args.cmd == "list":
        try:
            registry = Registry(args.registry)
        except Exception as e:
            print(f"DEAD: could not load registry: {e}", file=sys.stderr)
            return 2

        peers = registry.list_peers()
        if not peers:
            print("no peers registered")
            return 0

        for peer in peers:
            print(f"{peer.name:20} {' '.join(peer.endpoints):40} {peer.state.value}")

        return 0

    # GET: peer details
    if args.cmd == "get":
        try:
            registry = Registry(args.registry)
        except Exception as e:
            print(f"DEAD: could not load registry: {e}", file=sys.stderr)
            return 2

        peer = registry.get_peer(args.peer_name)
        if not peer:
            print(f"ERROR: no such peer: {args.peer_name}", file=sys.stderr)
            return 1

        print(json.dumps({
            "name": peer.name,
            "endpoints": peer.endpoints,
            "state": peer.state.value,
            "last_check_error": peer.last_check_error
        }, indent=2))

        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
