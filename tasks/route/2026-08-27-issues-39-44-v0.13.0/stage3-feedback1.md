boss レビュー（S3 差し戻し 1）— コード欠陥 5 点＋故障注入フックの定義＋テスト網羅の完遂。git 操作は不要（boss が行う）。
前回は依頼書 §1.6 の (i)〜(viii) の大半とフルスイート完走・revert 確認が未実施のまま終了した。**今回は §1.6 を全項目実装し、
フルスイートを完走させ、結果を報告するまで終えないこと。**

## A. コード欠陥（`skills/audit/scripts/import-audit-scope.py`）

1. **他者の lock を消し得る**（`acquire()` の except 節 `:211-214`）: flock 失敗や inode 不一致（`lock inode changed`）の後に
   `if os.path.exists(lock): os.unlink(lock)` を無条件に実行している。inode が変わった＝別プロセスの lock に置き換わった状況で
   その lock を消すことになる。**unlink は `os.fstat(fd).st_ino == os.lstat(lock).st_ino` のときだけ**に限定せよ（不一致なら
   触らない）。
2. **config 不在で `--base-config` なしでも空 config から作成してしまう**（`:263-269`）: `fresh is None` かつ `base is None` のとき
   `config_object(None)` → `{}` に impactMap と auditScope だけ足した config が生成される。仕様（PLAN §9）: config 不在の初回作成は
   `--base-config -`＋`--expect-base-config-sha` が**必須**。`fresh is None and base is None` は error（`config absent: use
   --base-config - with --expect-base-config-sha`）で exit 1・無変更にせよ。
3. **`report_pattern` の 6 複製目**（`report_regex()` `:111-120`）: report 除外の正規表現は既に 5 箇所に複製があり
   `tests/test_report_matcher_contract.py` で契約固定されている（PLAN §7「report_pattern に触る場合は複製＋契約テスト同時更新」）。
   この 6 複製目を**同契約テストの対象に追加**し、他複製と同じ入力で同じ判定になることを固定せよ（テストファイルの構造に従う）。
4. `datetime.datetime.now(datetime.UTC)` → 他スクリプトと同じ `datetime.timezone.utc` に統一（`:209,:273`）。
5. **可読性**: `;` で複数文を 1 行に詰めた記述（`:228-258,:263-284` など）を通常の 1 文 1 行に展開せよ（挙動は変えない）。
   `convert()` が `validate_rules` と `equivalence` で二重に呼ばれ同じ error が重複して並ぶ点も、変換結果をキャッシュして 1 回に
   まとめよ（`errors[]` に同文言が 2 回入らないこと）。

## B. 故障注入フック（テスト用・仕様化）
PLAN §6 (v) の「flock 保持中に `--break-lock` 拒否」「replace 前／後の故障」「flock 前 unlink」を実プロセスで検査するため、
環境変数 `DOCAUDIT_IMPORT_AUDIT_SCOPE_FAULT` を定義する（コード先頭のコメントで「テスト専用。本番では未設定」と明記）:
- `hold-lock:<path>` — lock 取得（flock＋inode 確認）直後、`<path>` のファイルが現れるまで 0.05 秒間隔で待つ（最大 30 秒）。
  テストはこの間に `open-run.py --break-lock` を実行して拒否（exit 4・`gate-running`）を確認し、その後 `<path>` を作成して
  importer を完走させる。
- `before-replace` — 一時ファイル書き込み後・`os.replace` 前に `OSError` を送出（→ 旧 config 不変・一時ファイル残存なし・lock 不在）。
- `after-replace` — `os.replace` 後・dir fsync で `OSError` を送出（→ 完成 JSON のみ存在・lock 不在。exit は非 0 で理由を stderr）。
- `unlink-before-flock` — `O_EXCL` 作成直後・flock 前に自分の lock path を unlink（→ inode 不一致で無変更停止 exit 3）。

## C. テスト網羅（依頼書 §1.6 の (i)〜(viii) をすべて。1 項目 1 テスト以上、`subTest` 可）
特に未実装の: (i) 反例の具体パス（`*/foo` vs root `foo`、`?` vs `a/b`）と合成パス集合 ≥ 12 件での一致／(ii) 偽 `git` による
「absent では git 0 回」と CR/LF 名 error・`equivalenceChecked ≥ 1`／(iii) 拒否 7 種＋report 除外の対試験＋CR/LF／(iv)／
(v) の全項目（fresh repo の run-base 作成 0o700、symlink `.claude/state` で exit 1、既存 lock exit 3、**B のフック 4 種**、expect
SHA 不一致 exit 4・無変更、`source` 項目置換と `note` 手書き項目保全、`--base-config -` の 3 ケース、**A-2 の error**）／(vi) drift
4 経路＋multiset＋metadata 型異常 6 種＋2 glob＋カンマ glob／(vii) 包含・symlink・custom scope／(viii) は S2 で追加済みか確認。
実物検査テスト（dir-framework が無い環境では skipTest）: tracked 46 件・24 規則・拒否 0・`state=not-imported`。

## D. 完了条件
- `python3 -m unittest discover -s tests -t .` を**完走**させ、`Ran N tests … OK (skipped=K)` の行を報告に貼る（着手前は 414 件・
  skip 6）。
- A-1／A-2／B の `hold-lock` について、実装を revert すると対応テストが赤になることを確認し方法を報告。
- テスト名⇔検査内容の対応表（(i)〜(viii) ごと）。

## E. モデル運用
本ラウンドは推論の深さを上げる（boss 側で `model_reasoning_effort=high` を指定）。作業量が多いので、報告は最後に 1 回で
よいが、**途中で止まらず**完了まで進めること。
