# Gate-(b) probe results — 2026-08-25T05:23:30Z

codex: codex-cli 0.149.0; CODEX_HOME=/Users/akiratakahashi/.codex-doc-audit-harness (via direnv)

## P1 happy path (--output-schema + -o, trivial prompt)
exit=0 ; -o file: EXISTS size=82B valid-JSON: {"verdict":"PASS","rationale":"probe run — no analysis performed","evidence":[]}

## P2 malformed schema file
exit=1 ; -o file: ABSENT ; stderr-tail: [0mdirenv: loading ~/Projects/doc-audit-harness/.envrc Output schema file /Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-28-37-release/probes/schema-malformed.json is not valid JSON: key must be a string at line 1 column 3 

## P3 kill mid-run (SIGTERM at 10s, slow prompt)
exit=143 ; -o file: ABSENT

## P4 -o into nonexistent parent dir
exit=0 ; -o file: ABSENT ; parent-dir: not-created ; stderr-tail: Failed to write last message file "/Users/akiratakahashi/Projects/doc-audit-harness/tasks/route/2026-08-25-issues-28-37-release/probes/no-such-dir/out4.json": No such file or directory (os error 2) tokens used 15,719 {"verdict":"PASS","rationale":"probe run — no analysis performed","evidence":[]} 

## P5 3x concurrent (-o out5a/b/c)
exits=0/0/0
out5a: EXISTS size=82B valid-JSON: {"verdict":"PASS","rationale":"probe run — no analysis performed","evidence":[]}
out5b: EXISTS size=82B valid-JSON: {"verdict":"PASS","rationale":"probe run — no analysis performed","evidence":[]}
out5c: EXISTS size=82B valid-JSON: {"verdict":"PASS","rationale":"probe run — no analysis performed","evidence":[]}

## done
