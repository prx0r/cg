# Worldpacks — distribution format

A worldpack is a versioned, content-addressed archive of a `cogym_kernel/worlds/<name>/` directory
(manifest.json + world.py + policies + tests). Publish:

```bash
python3 -m cogym_kernel.cli worldpack-export cogym_kernel/worlds/toy --out-dir worldpacks
# → worldpacks/toy-v1.tar.gz  (+ sha256 in stdout JSON)
cogym publish-worldpack worldpacks/toy-v1.tar.gz
```

Consumers: `worldpack install <hash>` fetches via IPFS/HTTP mirror, verifies hash, registers via `worlds/registry.py`.

Manifest (`manifest.json`) required fields:
```json
{"kind": "toy.signal_game", "name": "toy", "version": 1,
 "description": "…", "created": "2026-08-24T…", "content_hash": "sha256:…"}
```

All scenario hashes are version-pinned; cross-machine comparability is byte-level.

Known packs: `website/data/worldpacks.json` (rendered by the community site).
