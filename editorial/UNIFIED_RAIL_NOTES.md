# Unified editorial rail

All WordPress editorial work uses one guarded route:

`editorial/<slug>/config.json + content.html`
→ branch
→ Pull Request
→ diff/safety review
→ merge to `main`
→ `.github/workflows/apply-editorial-draft-packages-on-push.yml`
→ `scripts/apply_editorial_draft_once.py`
→ WordPress verification / Issue #22 audit

## New draft

Set `"operation": "create"` in `config.json`.

Safety invariants:

- no `post_id` in a create package
- WordPress status is always `draft`
- an existing post/page with the same slug blocks creation
- every inline WordPress media ID must be listed in `expected_media`
- expected media IDs are verified against their current WordPress source paths
- published post/page counts must remain unchanged
- the created post is fetched again and title / slug / content / status / categories / featured media are verified

## Existing draft update

Omit `operation` and provide the existing guarded update fields, including the exact `post_id` and `slug`.

The updater refuses unexpected status, slug, marker, content, title, or featured-media state instead of overwriting it silently.

## One implementation only

Do not create a separate `create.json` workflow, create-only script, or create-only rail.
Do not revive implementation names from old notes or conversation memory.
The current `main` branch is the implementation source of truth.
