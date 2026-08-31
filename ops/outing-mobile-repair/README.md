# Outing mobile repair

One-shot guarded repair for draft page 3154 after Gutenberg migration. It keeps the page as a draft, backs up the current raw content, patches only the canonical CSS, deploys through the existing outing deployer, verifies the required block markers and responsive CSS, and restores the backup automatically if verification fails.
