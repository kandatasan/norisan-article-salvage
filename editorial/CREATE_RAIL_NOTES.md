## Safety invariants

- New editorial packages create WordPress posts only with `status=draft`.
- The rail refuses to overwrite an existing draft with the same slug if its title/content/featured image differ.
- Existing published, pending, private, or scheduled posts with the same slug block creation.
- Published post/page counts are checked before and after creation and must remain unchanged.
- Existing article edits continue to use the separate guarded `config.json` update rail.
