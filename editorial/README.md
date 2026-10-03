# Editorial packages

New WordPress drafts are created from guarded editorial packages containing `create.json` and `content.html`.
After creation, promote the package to the guarded update rail by adding `config.json` with the returned `post_id` and removing or retiring `create.json` as appropriate.

The create rail must only create `draft` posts and must never publish content directly.
