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
