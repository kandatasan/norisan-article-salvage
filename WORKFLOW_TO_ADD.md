# Manual GitHub Actions workflow step

GitHub Actions workflow files cannot be written by the connected assistant integration. Add the provided workflow manually at:

`.github/workflows/tsurikue-dead-link-cleanup.yml`

Use the exact reviewed YAML supplied in the conversation. Do not run apply yet. First merge the PR, then run `authenticated-dry-run` and verify the expected 10 documents / 23 links / 22 block removals / 1 anchor unwrap / 0 remaining count.
