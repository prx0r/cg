#!/usr/bin/env python3
"""Export a world as a versioned, content-addressed Worldpack artifact.

A worldpack = tar.gz of the world directory (world.py, policies, manifest,
README, AGENTS.md) + content hash + clone/replay instructions. Published to
website/data/worldpacks.json so anyone can:
    git clone <repo> && git checkout <commit>
    tar xzf worldpacks/<kind>-<version>.tgz -C cogym_kernel/worldpacks/
    cogym run --world <kind> --suite manifest.json
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile

WORLDS = "/root/cogym/canonical/cogym/worlds"
OUT_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "website", "data")


def dir_hash(path: str) -> str:
    h = hashlib.sha256()
    for root, _, files in sorted(os.walk(path)):
        for f in sorted(files):
            fp = os.path.join(root, f)
            h.update(os.path.relpath(fp, path).encode())
            h.update(open(fp, "rb").read())
    return h.hexdigest()


def export(kind: str) -> dict:
    name = kind.split(".")[0]
    src = os.path.join(WORLDS, name)
    if not os.path.isdir(src):
        raise SystemExit(f"world dir not found: {src}")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd="/root/cogym",
                            capture_output=True, text=True).stdout.strip()
    version = 1
    out_dir = os.path.join(OUT_DATA, "..", "..", "worldpacks")
    os.makedirs(out_dir, exist_ok=True)
    artifact = os.path.join(out_dir, f"{kind}-v{version}.tar.gz")
    with tarfile.open(artifact, "w:gz") as tf:
        for f in ("manifest.json", "world.py", "__init__.py", "README.md",
                  "AGENTS.md", "experience.py", "runner.py"):
            fp = os.path.join(src, f)
            if os.path.exists(fp):
                tf.add(fp, arcname=f"{kind}/{f}")
    art_hash = hashlib.sha256(open(artifact, "rb").read()).hexdigest()
    manifest = json.load(open(os.path.join(src, "manifest.json")))
    return {
        "kind": kind,
        "version": str(version),
        "description": manifest.get("description", ""),
        "content_hash": f"sha256:{art_hash}",
        "artifact": os.path.basename(artifact),
        "git_repo": "https://github.com/prx0r/cogym.git",
        "git_commit": commit,
        "replay": [
            f"git clone {manifest.get('git_repo', '')} cogym-lab || true",
            f"cd cogym-lab && git checkout {commit}",
            f"tar xzf worldpacks/{os.path.basename(artifact)}",
            f"cd canonical && python3 -m cogym.worlds.{name}.runner --generations 2",
        ],
    }


def main() -> int:
    packs = []
    for d in sorted(os.listdir(WORLDS)):
        if os.path.exists(os.path.join(WORLDS, d, "manifest.json")):
            try:
                packs.append(export(f"{d}.signal_game"))
            except SystemExit:
                continue
    # built-in worlds without scaffold manifests
    packs.insert(0, {"kind": "toy.search_game", "version": "1",
                     "description": "10 hidden boxes; find prize at minimum probe cost",
                     "content_hash": "builtin:core",
                     "git_repo": "https://github.com/prx0r/cogym.git",
                     "git_commit": subprocess.run(["git", "rev-parse", "HEAD"],
                                                  cwd="/root/cogym",
                                                  capture_output=True,
                                                  text=True).stdout.strip(),
                     "replay": ["cd canonical",
                                "python3 -m pytest tests/test_generic_core.py -q"]})
    json.dump(packs, open(os.path.join(OUT_DATA, "worldpacks.json"), "w"),
              indent=2)
    print(json.dumps([{"kind": p["kind"], "hash": p["content_hash"][:19]}
                      for p in packs], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
