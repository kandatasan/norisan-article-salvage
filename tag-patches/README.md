# Tag-only WordPress patches

This directory is for **add-only WordPress tag changes** that must not rewrite
article content.

The updater:

- targets one exact `post_id` + `slug`
- allows only `draft` or `publish` posts
- preserves every existing tag
- adds only the requested tags
- can create a missing WordPress tag only when `allow_create_tags` is `true`
- sends only the `tags` field when updating the post
- verifies title, content hash, featured image, slug, and status are unchanged
- verifies published post/page counts are unchanged
- records the result on salvage audit Issue #22

It does **not** support tag removal or tag replacement.

## Example config

Create `tag-patches/<post-slug>/config.json`:

```json
{
  "post_id": 1234,
  "slug": "lexus-ux-review",
  "expected_status": "publish",
  "mode": "add_only",
  "allow_create_tags": true,
  "tags": [
    {
      "name": "レクサスUX",
      "slug": "lexus-ux"
    },
    {
      "name": "中古車",
      "slug": "used-car"
    }
  ]
}
```

A tag can also be written as a simple string when an explicit slug is not
needed:

```json
{
  "post_id": 1234,
  "slug": "lexus-ux-review",
  "mode": "add_only",
  "allow_create_tags": true,
  "tags": ["レクサスUX", "中古車"]
}
```

For stable taxonomy management, an explicit English slug is preferred for new
tags.

## Safety behavior

If the configured tag already exists, the existing term ID is reused. If a
configured name already exists under a different explicit slug, the run stops
instead of creating a duplicate-looking tag.

If `allow_create_tags` is omitted or `false`, a missing tag blocks the run.

`expected_status` is optional. When supplied, it adds an extra guard so a
package intended for a published post cannot silently run against a draft, or
vice versa.
