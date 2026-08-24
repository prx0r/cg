# cogymkernel community site

Static, zero-build. Deploy: `npx wrangler pages deploy website --project-name=cogymkernel-claims`
(config in `website/wrangler.toml`). Local preview: `python3 -m http.server -d website 8080`.

## What it shares

- **CapabilityClaims** (`data/claims/*.json`, indexed by `data/claims.json`)
  — schema `claims/schema.v1.json`. Verifiable: replay the committed
  world+candidate, diff receipt hashes.
- **Worldpacks** (`data/worldpacks.json`) — distributable scenario packages.

## Publishing flow

1. Run an experiment cycle in a cogym lab (verification tiers included).
2. `cogym claim create <cycle_dir> --out claim.json` (kernel CLI; M4).
3. Validate against `claims/schema.v1.json`.
4. PR the JSON into `website/data/claims/` — CI re-validates and re-renders.

No server, no database: claims are files; the site is their window.

## Reproducibility contract

Every claim embeds: git repo + exact commit, world path, dependency lock hash,
python version, verbatim API transcript hashes, and the re-execute command.
CI (`.github/workflows/validate-claims.yml`) enforces:
1. jsonschema validation of every published claim
2. claim_id content-hash determinism (tamper detection)

Verifiers clone the repo at the pinned commit, checkout the worldpack hash,
run the command, and diff receipt hashes. Mismatch = refuted claim.

## Worldpacks

`tools/export_worldpacks.py` bundles registered worlds into `worldpacks/*.tar.gz`
with sha256 + replay instructions, indexed in `data/worldpacks.json`.
