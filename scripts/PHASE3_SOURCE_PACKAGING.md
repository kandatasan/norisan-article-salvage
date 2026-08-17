# Phase 3 source packaging

Issue #15 のリメイク元データは、GitHub connector で安全に転送できるサイズにするため `old_tsurikue_remake_sources.bz2.b64.part01` 〜 `part08` に分割して保存しています。

`old_tsurikue_remake_dry_run.py` はファイル名順に連結し、Base64 decode → bz2 decompress → JSON decode します。

Phase 2 の確定写真110件も `old_tsurikue_phase2_photo_matches.bz2.b64` に圧縮保存し、既存の `old_tsurikue_recovered_photo_refs.tsv`（363件）と組み合わせて 110 MATCH_FILENAME / 253 unmatched を再構成します。

この包装はデータ転送方法だけの変更で、Phase 3 の出力仕様は 46記事 / 110一致画像 / 29プレースホルダー / 224写真省略 / WordPress write 0 のままです。
