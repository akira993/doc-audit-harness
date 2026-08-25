import importlib.util, json, os, subprocess, sys, tempfile, unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "audit", "scripts", "generic-layers.py")


def load_script_module():
    # The script has a hyphen in its name; load it by path so tests can call
    # extract_links() directly (e.g. to assert exact line numbers).
    spec = importlib.util.spec_from_file_location("generic_layers_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(repo, layer="all", config=None, paths=None):
    cfg = config or {"docGlobs": ["docs/**/*.md", "*.md"]}
    cf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(cfg, cf); cf.close()
    argv = [sys.executable, SCRIPT, "--config", cf.name, "--repo-root", repo, "--layer", layer]
    inp = None
    if paths is not None:
        argv += ["--paths", "-"]; inp = "\n".join(paths)
    p = subprocess.run(argv, input=inp, capture_output=True, text=True)
    os.unlink(cf.name)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def run_text(repo, layer="all", config=None, paths=None):
    cfg = config or {"docGlobs": ["docs/**/*.md", "*.md"]}
    cf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(cfg, cf); cf.close()
    argv = [sys.executable, SCRIPT, "--config", cf.name, "--repo-root", repo,
            "--layer", layer, "--format", "text"]
    inp = None
    if paths is not None:
        argv += ["--paths", "-"]; inp = "\n".join(paths)
    p = subprocess.run(argv, input=inp, capture_output=True, text=True)
    os.unlink(cf.name)
    assert p.returncode == 0, p.stderr
    return p.stdout


def write(repo, rel, content):
    full = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(full) or repo, exist_ok=True)
    open(full, "w", encoding="utf-8").write(content)


class TestFormatLayer(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_broken_relative_link_is_fail(self):
        write(self.repo, "docs/a.md", "see [x](./missing.md)\n")
        out = run(self.repo, "format")
        fails = [f for f in out["findings"] if f["severity"] == "FAIL"]
        self.assertTrue(any("missing.md" in f["message"] for f in fails))

    def test_resolving_link_no_finding(self):
        write(self.repo, "docs/a.md", "see [b](./b.md)\n")
        write(self.repo, "docs/b.md", "hi\n")
        out = run(self.repo, "format")
        self.assertEqual([f for f in out["findings"] if f["severity"] == "FAIL"], [])

    def test_external_link_skipped(self):
        write(self.repo, "docs/a.md", "see [g](https://example.com/x)\n")
        out = run(self.repo, "format")
        self.assertEqual(out["findings"], [])

    def test_frontmatter_field_warn_when_configured(self):
        write(self.repo, "docs/a.md", "---\ntitle: x\n---\nbody\n")
        out = run(self.repo, "format", config={"docGlobs": ["docs/**/*.md", "*.md"],
                                               "frontMatterFields": ["title", "version"]})
        warns = [f for f in out["findings"] if f["severity"] == "WARN"]
        self.assertTrue(any("version" in f["message"] for f in warns))
        self.assertFalse(any("title" in f["message"] for f in warns))

    def test_no_frontmatter_check_when_not_configured(self):
        write(self.repo, "docs/a.md", "no front matter here\n")
        out = run(self.repo, "format")
        self.assertEqual([f for f in out["findings"] if "front matter" in f["message"]], [])


class TestExistenceLayer(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.repo, "scripts"), exist_ok=True)
        open(os.path.join(self.repo, "scripts", "real.py"), "w").write("x\n")

    def test_nonresolving_repo_pathish_token_warns(self):
        write(self.repo, "docs/a.md", "see `scripts/ghost.py` for details\n")
        out = run(self.repo, "existence")
        self.assertTrue(any("scripts/ghost.py" in f["message"] for f in out["findings"]))

    def test_resolving_token_no_finding(self):
        write(self.repo, "docs/a.md", "see `scripts/real.py`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_non_path_backtick_ignored(self):
        write(self.repo, "docs/a.md", "run `make deploy` then `occ status`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_glob_token_skipped(self):
        write(self.repo, "docs/a.md", "edit `scripts/*.py`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_file_line_locator_with_existing_base_no_warn(self):
        write(self.repo, "docs/real.md", "x\n")
        write(self.repo, "docs/a.md", "see `docs/real.md:18,25-34`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_file_symbol_locator_with_existing_base_no_warn(self):
        write(self.repo, "apps/worker/src/index.ts", "x\n")
        write(self.repo, "docs/a.md", "see `apps/worker/src/index.ts:SYMBOL`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_existing_filename_with_colon_resolves_before_locator_split(self):
        write(self.repo, "docs/foo:bar", "x\n")
        write(self.repo, "docs/a.md", "see `docs/foo:bar`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_ellipsis_shorthand_skipped(self):
        write(self.repo, "apps/worker/src/index.ts", "x\n")  # makes apps/ a real top dir
        write(self.repo, "docs/a.md", "see `apps/admin/src/x/...`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_brace_shorthand_skipped(self):
        write(self.repo, "docs/a.md", "see `docs/{a,b}.md`\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_locator_with_missing_base_still_warns(self):
        # The base path must still be checked: a locator does not excuse a
        # genuinely missing file.
        write(self.repo, "docs/a.md", "see `docs/ghost.md:42`\n")
        out = run(self.repo, "existence")
        self.assertTrue(any("docs/ghost.md:42" in f["message"] for f in out["findings"]))

    def test_locators_and_shorthand_only_flag_genuine_miss(self):
        write(self.repo, "docs/real.md", "x\n")
        write(self.repo, "apps/worker/src/index.ts", "x\n")
        write(self.repo, "docs/t.md",
              "`docs/real.md:18,25-34`\n"        # file:line, base exists -> NO warn
              "`apps/worker/src/index.ts:SYMBOL`\n"  # file:symbol, base exists -> NO warn
              "`apps/admin/src/x/...`\n"         # ellipsis -> NO warn
              "`docs/{a,b}.md`\n"                # brace -> NO warn
              "`docs/missing-real.md`\n"         # genuinely missing -> WARN (kept)
              "`apps/worker/src/index.ts`\n")    # exists -> NO warn
        out = run(self.repo, "existence")
        msgs = [f["message"] for f in out["findings"]]
        self.assertEqual(len(msgs), 1, msgs)
        self.assertIn("docs/missing-real.md", msgs[0])


class TestSemanticLayer(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_orphan_doc_warns(self):
        write(self.repo, "docs/README.md", "index: [a](./a.md)\n")
        write(self.repo, "docs/a.md", "linked\n")
        write(self.repo, "docs/orphan.md", "nobody links me\n")
        out = run(self.repo, "semantic")
        msgs = [(f["path"], f["message"]) for f in out["findings"]]
        self.assertTrue(any(p == "docs/orphan.md" for p, _ in msgs))
        self.assertFalse(any(p == "docs/a.md" for p, _ in msgs))

    def test_index_file_not_orphan(self):
        write(self.repo, "docs/README.md", "nothing links the index itself\n")
        out = run(self.repo, "semantic")
        self.assertFalse(any(f["path"] == "docs/README.md" for f in out["findings"]))

    def test_all_layer_counts(self):
        write(self.repo, "docs/README.md", "[a](./a.md)\n")
        write(self.repo, "docs/a.md", "see [x](./gone.md) and `scripts/ghost.py`\n")
        os.makedirs(os.path.join(self.repo, "scripts"), exist_ok=True)
        out = run(self.repo, "all")
        self.assertGreaterEqual(out["counts"]["fail"], 1)   # broken link gone.md
        self.assertIn("findings", out)
        self.assertEqual(out["counts"]["findings"], len(out["findings"]))


class TestPlan2Fixes(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_titled_link_not_broken(self):
        write(self.repo, "docs/a.md", 'see [b](./b.md "My Title")\n')
        write(self.repo, "docs/b.md", "x\n")
        out = run(self.repo, "format")
        self.assertEqual([f for f in out["findings"] if f["severity"] == "FAIL"], [])

    def test_semantic_paths_scope_no_false_orphan(self):
        write(self.repo, "docs/README.md", "[a](./a.md)\n")
        write(self.repo, "docs/a.md", "linked\n")
        out = run(self.repo, "semantic", paths=["docs/a.md"])  # README excluded from --paths scope
        self.assertFalse(any(f["path"] == "docs/a.md" for f in out["findings"]))

    def test_index_outside_docglobs_resolves_orphan_full_scan(self):
        write(self.repo, "index.txt", "[target](docs/target.md)\n")
        write(self.repo, "docs/target.md", "linked from external index\n")
        out = run(self.repo, "semantic", config={"docGlobs": ["docs/**/*.md"],
                                                   "indexFiles": ["./index.txt"]})
        self.assertFalse(any(f["path"] == "docs/target.md" for f in out["findings"]))

    def test_index_outside_docglobs_resolves_orphan_incremental_stdin(self):
        write(self.repo, "index.txt", "[target](docs/target.md)\n")
        write(self.repo, "docs/target.md", "linked from external index\n")
        out = run(self.repo, "semantic", config={"docGlobs": ["docs/**/*.md"],
                                                   "indexFiles": ["./index.txt"]},
                  paths=["docs/target.md"])
        self.assertFalse(any(f["path"] == "docs/target.md" for f in out["findings"]))

    def test_invalid_index_files_warn_and_are_excluded(self):
        os.makedirs(os.path.join(self.repo, "indexes"), exist_ok=True)
        entries = ["missing.md", "../outside.md", os.path.join(self.repo, "absolute.md"), "indexes"]
        write(self.repo, "docs/target.md", "target\n")
        out = run(self.repo, "semantic", config={"docGlobs": ["docs/**/*.md"],
                                                   "indexFiles": entries})
        warns = [f for f in out["findings"] if f["severity"] == "WARN" and f["message"].startswith("indexFiles")]
        self.assertEqual(len(warns), 4)
        self.assertTrue(any("does not exist" in f["message"] for f in warns))
        self.assertTrue(any("outside the repository" in f["message"] for f in warns))
        self.assertTrue(any("regular file" in f["message"] for f in warns))

    def test_index_symlink_resolving_outside_repo_warns_and_does_not_rescue_orphan(self):
        outside = tempfile.mkdtemp()
        write(outside, "index.md", "[target](docs/target.md)\n")
        os.symlink(os.path.join(outside, "index.md"), os.path.join(self.repo, "index-link.md"))
        write(self.repo, "docs/target.md", "target\n")
        out = run(self.repo, "semantic", config={"docGlobs": ["docs/**/*.md"],
                                                   "indexFiles": ["index-link.md"]})
        warns = [f for f in out["findings"] if f["path"] == "index-link.md"]
        self.assertTrue(any("resolves outside the repository" in f["message"] for f in warns))
        self.assertTrue(any(f["path"] == "docs/target.md" and f["message"].startswith("orphan:")
                            for f in out["findings"]))

    def test_hyphenated_frontmatter_field_found(self):
        write(self.repo, "docs/a.md", "---\nx-custom: y\n---\nbody\n")
        out = run(self.repo, "format", config={"docGlobs": ["docs/**/*.md", "*.md"],
                                               "frontMatterFields": ["x-custom"]})
        self.assertFalse(any("x-custom" in f["message"] for f in out["findings"]))


    def test_node_modules_skipped(self):
        # Broad docGlobs must not scan node_modules (no findings from vendored md).
        os.makedirs(os.path.join(self.repo, "node_modules", "pkg"), exist_ok=True)
        write(self.repo, "node_modules/pkg/x.md", "see [a](./gone.md)\n")
        write(self.repo, "docs/a.md", "ok\n")
        out = run(self.repo, "all", config={"docGlobs": ["**/*.md"]})
        self.assertFalse(any("node_modules" in f["path"] for f in out["findings"]))


class TestLinksInsideCodeIgnored(unittest.TestCase):
    """Markdown link *examples* written inside code (inline spans / fenced blocks)
    are literal text, not links — they must not trip the broken-link check, and
    suppressing them must not shift the line numbers of real links."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()

    # --- unit level: extract_links() masking + exact line numbers ---------------
    def test_extract_links_masks_code_keeps_line_numbers(self):
        mod = load_script_module()
        doc = (
            "# T\n"                                  # L1
            "[a](./missing-real.md)\n"               # L2: real link
            "inline `[b](./missing-inline.md)`\n"    # L3: inline code -> ignored
            "```\n[c](./missing-fence.md)\n```\n"    # L4-6: fenced -> ignored
            "[d](./missing-real2.md)\n"              # L7: real link
        )
        links = mod.extract_links(doc)
        self.assertIn(("./missing-real.md", 2), links)
        self.assertIn(("./missing-real2.md", 7), links)
        self.assertTrue(all("inline" not in t and "fence" not in t for t, _ in links))

    def test_extract_links_tilde_fence_and_lang_tag_indent(self):
        mod = load_script_module()
        doc = (
            "intro\n"                                # L1
            "~~~js\n[x](./in-tilde.md)\n~~~\n"       # L2-4: tilde fence -> ignored
            "   ```python\n   [y](./in-indented.md)\n   ```\n"  # L5-7: indented backtick fence
            "[real](./after.md)\n"                   # L8: real link
        )
        links = mod.extract_links(doc)
        self.assertEqual([("./after.md", 8)], links)

    def test_extract_links_multi_backtick_inline_run(self):
        mod = load_script_module()
        doc = "use ``[z](./nested.md)`` here and [real](./r.md)\n"
        links = mod.extract_links(doc)
        self.assertEqual([("./r.md", 1)], links)

    def test_extract_links_stray_backtick_does_not_swallow_real_link(self):
        # A lone/unbalanced backtick must NOT mask a real link several lines later
        # (over-masking would silently weaken detection).
        mod = load_script_module()
        doc = (
            "a stray ` backtick\n"        # L1: unbalanced single backtick
            "[real](./gone.md)\n"         # L2: must still be detected
            "more text here\n"            # L3
        )
        links = mod.extract_links(doc)
        self.assertIn(("./gone.md", 2), links)

    # --- integration level: format layer end-to-end ----------------------------
    def test_format_inline_code_link_not_fail(self):
        write(self.repo, "docs/a.md", "see `[b](./does-not-exist.md)` example\n")
        out = run(self.repo, "format")
        self.assertEqual([f for f in out["findings"] if f["severity"] == "FAIL"], [])

    def test_format_fenced_block_link_not_fail(self):
        write(self.repo, "docs/a.md", "```\n[c](./nope.md)\n```\n")
        out = run(self.repo, "format")
        self.assertEqual([f for f in out["findings"] if f["severity"] == "FAIL"], [])

    def test_format_real_broken_link_still_fails_with_code_examples(self):
        write(self.repo, "docs/a.md",
              "intro\n"
              "`[ex](./code-example.md)`\n"      # L2: inline example -> ignored
              "```\n[ex2](./fence-example.md)\n```\n"  # L3-5: fence example -> ignored
              "[broken](./really-missing.md)\n")  # L6: real broken link -> FAIL @ L6
        out = run(self.repo, "format")
        fails = [f for f in out["findings"] if f["severity"] == "FAIL"]
        self.assertEqual(len(fails), 1)
        self.assertIn("really-missing.md", fails[0]["message"])
        self.assertEqual(fails[0]["line"], 6)

    # --- semantic regression: code-example links must not count as references ---
    def test_semantic_code_example_link_does_not_rescue_orphan(self):
        # README links a.md for real, but only *mentions* orphan.md inside a code
        # block; orphan.md must still be flagged (code link is not a real reference).
        write(self.repo, "docs/README.md",
              "index: [a](./a.md)\n```\n[o](./orphan.md)\n```\n")
        write(self.repo, "docs/a.md", "linked\n")
        write(self.repo, "docs/orphan.md", "nobody really links me\n")
        out = run(self.repo, "semantic")
        paths = {f["path"] for f in out["findings"]}
        self.assertIn("docs/orphan.md", paths)
        self.assertNotIn("docs/a.md", paths)


class TestIssue33Paths(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_four_reference_forms_have_exact_severity_path_and_line(self):
        write(self.repo, "docs/README.md",
              "[link](./gone-link.md)\n"
              "`docs/gone-code.md`\n"
              "docs/gone-bare.md — 説明\n"
              "`docs/gone-dir/`\n")
        out = run(self.repo, "all")
        self.assertEqual(
            [(f["layer"], f["severity"], f["path"], f["line"]) for f in out["findings"]],
            [("format", "FAIL", "docs/README.md", 1),
             ("existence", "FAIL", "docs/README.md", 2),
             ("existence", "WARN", "docs/README.md", 4),
             ("existence", "WARN", "docs/README.md", 3)])
        self.assertIn("bare path reference", out["findings"][3]["message"])
        self.assertEqual(out["counts"], {"docs": 1, "findings": 4, "fail": 2, "warn": 2})

    def test_bare_positive_boundaries_and_command_destination(self):
        cases = [
            ("「docs/gone.md」\n", 1),
            ("intro\ndocs/gone.mdを参照\n", 2),
            ("intro\nmore\n- docs/logs/gone.md — 説明\n", 3),
            ("cp docs/source.md docs/new.md\n", 1),
        ]
        for content, line in cases:
            with self.subTest(content=content):
                repo = tempfile.mkdtemp()
                write(repo, "docs/a.md", content)
                if content.startswith("cp "):
                    write(repo, "docs/source.md", "source\n")
                out = run(repo, "existence")
                self.assertEqual(len(out["findings"]), 1)
                finding = out["findings"][0]
                self.assertEqual((finding["severity"], finding["path"], finding["line"]),
                                 ("WARN", "docs/a.md", line))
                self.assertIn("bare path reference", finding["message"])

    def test_bare_false_positives_are_masked_or_resolve(self):
        write(self.repo, "docs/api.md", "api\n")
        write(self.repo, "docs/foo+bar.md", "plus\n")
        write(self.repo, "docs/foo bar.md", "space\n")
        write(self.repo, "docs/a.md",
              "docs/api.md（旧版）\n"
              "docs/api.md?raw=1\n"
              "docs/foo+bar.md\n"
              "docs/foo%20bar.md\n"
              "https://example.comを参照。docs/api.md\n"
              "https://docs/gone.md\n"
              "//docs/gone.md\n"
              "https://example.com/?next=docs/gone.md\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_non_ascii_bare_is_not_harvested_but_backtick_is_fail(self):
        write(self.repo, "docs/a.md", "docs/旧概要.md\n`docs/旧概要.md`\n")
        out = run(self.repo, "existence")
        self.assertEqual(
            [(f["severity"], f["path"], f["line"]) for f in out["findings"]],
            [("FAIL", "docs/a.md", 2)])

    def test_percent_decode_safety_inputs_do_not_stop_audit(self):
        write(self.repo, "docs/a.md", "`docs/%00.md`\n`docs/%2e%2e/x.md`\n")
        out = run(self.repo, "existence")
        self.assertEqual(
            [(f["severity"], f["path"], f["line"]) for f in out["findings"]],
            [("FAIL", "docs/a.md", 1), ("FAIL", "docs/a.md", 2)])

    def test_filesystem_exception_skips_token(self):
        mod = load_script_module()
        os.makedirs(os.path.join(self.repo, "docs"), exist_ok=True)
        original = mod.os.path.exists

        def raising(path):
            if "bad.md" in path:
                raise ValueError("injected")
            return original(path)

        with mock.patch.object(mod.os.path, "exists", side_effect=raising):
            self.assertEqual(mod._resolve_path_token("docs/bad.md", self.repo), (None, None))
        self.assertEqual(mod._resolve_path_token("docs/bad\x00.md", self.repo), (None, None))

    def test_normalization_order_drives_fail_classification(self):
        write(self.repo, "docs/a.md",
              "`docs/gone.md?raw=1`\n"
              "`docs/gone.md#x`\n"
              "`docs/gone.md:12`\n"
              "`docs/gone%2Emd`\n")
        out = run(self.repo, "existence")
        self.assertEqual(
            [(f["severity"], f["path"], f["line"]) for f in out["findings"]],
            [("FAIL", "docs/a.md", 1), ("FAIL", "docs/a.md", 2),
             ("FAIL", "docs/a.md", 3), ("FAIL", "docs/a.md", 4)])

    def test_existence_masks_all_specified_code_forms(self):
        write(self.repo, "docs/a.md",
              "```\n`docs/fenced.md`\n```\n"
              "    `docs/indented.md`\n"
              "> ```\n> `docs/quoted.md`\n> ```\n"
              "- ```\n- `docs/list.md`\n- ```\n"
              "- > ```\n- > `docs/nested.md`\n- > ```\n"
              "1) ```\n1) `docs/ordered.md`\n1) ```\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_file_directory_boundary_is_exact(self):
        write(self.repo, "docs/a.md",
              "`docs/LICENSE`\n`docs/v1.2`\n`docs/schema.d`\n`docs/gone/`\n")
        out = run(self.repo, "existence")
        self.assertEqual(
            [(f["severity"], f["path"], f["line"]) for f in out["findings"]],
            [("WARN", "docs/a.md", 1), ("WARN", "docs/a.md", 2),
             ("FAIL", "docs/a.md", 3), ("WARN", "docs/a.md", 4)])

    def test_parent_segments_and_external_symlink_are_skipped(self):
        outside = tempfile.mkdtemp()
        os.makedirs(os.path.join(outside, "target"), exist_ok=True)
        os.makedirs(os.path.join(self.repo, "docs"), exist_ok=True)
        os.symlink(os.path.join(outside, "target"), os.path.join(self.repo, "docs", "external"))
        write(self.repo, "docs/a.md",
              "`docs/../secret.md`\n"
              "docs/../secret.md\n"
              "`docs/external/gone.md`\n"
              "docs/external/gone.md\n")
        out = run(self.repo, "existence")
        self.assertEqual(out["findings"], [])

    def test_backtick_and_bare_are_disjoint_and_shorthand_order_is_stable(self):
        write(self.repo, "docs/a.md",
              "`docs/gone.md`\n"
              "docs/gone.md.\n"
              "docs/.../gone.md.\n"
              "docs/*.md.\n"
              "docs/{a,b}.md.\n")
        out = run(self.repo, "existence")
        self.assertEqual(
            [(f["severity"], f["path"], f["line"]) for f in out["findings"]],
            [("FAIL", "docs/a.md", 1), ("WARN", "docs/a.md", 2)])


class TestIssue34LayerConfiguration(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def test_layer_excludes_apply_inside_each_check(self):
        cfg = {"docGlobs": ["docs/**/*.md"],
               "layerGlobs": {
                   "format": {"exclude": ["docs/format.md"]},
                   "existence": {"exclude": ["docs/existence.md"]},
                   "semantic": {"exclude": ["docs/orphan.md"]}}}
        write(self.repo, "docs/format.md", "[gone](./gone.md)\n")
        write(self.repo, "docs/existence.md", "`docs/gone.md`\n")
        write(self.repo, "docs/README.md", "index\n")
        write(self.repo, "docs/orphan.md", "orphan\n")
        self.assertEqual(run(self.repo, "format", cfg, paths=["docs/format.md"])["findings"], [])
        self.assertEqual(run(self.repo, "existence", cfg, paths=["docs/existence.md"])["findings"], [])
        semantic = run(self.repo, "semantic", cfg, paths=["docs/orphan.md"])
        self.assertFalse(any(f["path"] == "docs/orphan.md" for f in semantic["findings"]))

    def test_semantic_excluded_doc_still_contributes_outgoing_links(self):
        cfg = {"docGlobs": ["docs/**/*.md"], "indexFiles": ["docs/README.md"],
               "layerGlobs": {"semantic": {"exclude": ["docs/source.md"]}}}
        write(self.repo, "docs/README.md", "index\n")
        write(self.repo, "docs/source.md", "[target](./target.md)\n")
        write(self.repo, "docs/target.md", "target\n")
        out = run(self.repo, "semantic", cfg)
        self.assertEqual(out["findings"], [])

    def test_front_matter_overrides_are_first_match_and_fallback(self):
        cfg = {"docGlobs": ["docs/**/*.md"], "frontMatterFields": ["version"],
               "frontMatterOverrides": [
                   {"globs": ["docs/skip.md", "docs/alternate.md"], "fields": []},
                   {"globs": ["docs/first.md", "guide/first.md"], "fields": ["title"]},
                   {"globs": ["docs/first.md"], "fields": ["version"]}]}
        write(self.repo, "docs/skip.md", "no front matter\n")
        write(self.repo, "docs/alternate.md", "also no front matter\n")
        write(self.repo, "docs/first.md", "---\ntitle: yes\n---\nbody\n")
        write(self.repo, "docs/fallback.md", "---\ntitle: only\n---\nbody\n")
        out = run(self.repo, "format", cfg)
        self.assertEqual(
            [(f["severity"], f["path"], f["line"], f["message"]) for f in out["findings"]],
            [("WARN", "docs/fallback.md", 1, "front matter missing field: version")])

    def test_invalid_new_config_parts_each_warn_once(self):
        cases = [
            ({"layerGlobs": []}, "layerGlobs"),
            ({"layerGlobs": {"format": []}}, "layerGlobs.format"),
            ({"layerGlobs": {"format": {"exclude": "docs/**"}}}, "exclude"),
            ({"layerGlobs": {"format": {"exclude": [1]}}}, "non-string"),
            ({"frontMatterOverrides": {}}, "frontMatterOverrides"),
            ({"frontMatterOverrides": [{"globs": [1], "fields": []}]}, "entry"),
        ]
        write(self.repo, "docs/a.md", "ok\n")
        for extra, message_part in cases:
            with self.subTest(extra=extra):
                cfg = {"docGlobs": ["docs/**/*.md"]}
                cfg.update(extra)
                out = run(self.repo, "format", cfg)
                self.assertEqual(len(out["findings"]), 1)
                finding = out["findings"][0]
                self.assertEqual((finding["severity"], finding["path"], finding["line"]),
                                 ("WARN", "(config)", 1))
                self.assertIn(message_part, finding["message"])

    def test_unknown_keys_are_ignored_and_text_pass_ignores_config_path(self):
        cfg = {"docGlobs": ["docs/**/*.md"], "layerGlobs": {"format": {"unknown": 1}},
               "frontMatterOverrides": {}, "unknown": True}
        write(self.repo, "docs/a.md", "ok\n")
        output = run_text(self.repo, "format", cfg)
        self.assertIn("HIT WARN (config):1", output)
        self.assertIn("SUMMARY pass=1 warn=1 fail=0", output)


class TestIssue35GenericReportCorpus(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.mod = load_script_module()

    def config(self, report="docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md", **extra):
        cfg = {"docGlobs": ["docs/**/*.md"], "reportPath": report}
        cfg.update(extra)
        return cfg

    def test_report_matcher_contract_with_explicit_suffix_position(self):
        rx = self.mod.report_pattern(self.config())
        cases = {
            "docs/logs/doc_audit_2026-08-25.md": True,
            "docs/logs/doc_audit_2026-08-25_02.md": True,
            "docs/logs/doc_audit_2026-08-25_100.md": True,
            "docs/logs/doc_audit_2026-08-25_2.md": False,
            "docs/logs/doc_audit_policy.md": False,
            "docs/logs/doc_audit_２０２６-０８-２５.md": False,
            "docs/logs/doc_audit_2026-08-25.txt": False,
        }
        self.assertEqual({path: bool(rx and self.mod.re.fullmatch(rx, path)) for path in cases}, cases)

        positioned = self.mod.report_pattern(self.config(
            "docs/logs/audit_<YYYY-MM-DD>_final[_NN].md"))
        self.assertTrue(self.mod.re.fullmatch(positioned, "docs/logs/audit_2026-08-25_final_02.md"))
        self.assertFalse(self.mod.re.fullmatch(positioned, "docs/logs/audit_2026-08-25_02_final.md"))

    def test_report_matcher_without_suffix_inserts_after_basename_date(self):
        rx = self.mod.report_pattern(self.config("docs/logs/audit_<YYYY-MM-DD>_final.md"))
        self.assertTrue(self.mod.re.fullmatch(rx, "docs/logs/audit_2026-08-25_final.md"))
        self.assertTrue(self.mod.re.fullmatch(rx, "docs/logs/audit_2026-08-25_02_final.md"))
        self.assertFalse(self.mod.re.fullmatch(rx, "docs/logs/audit_2026-08-25_final_02.md"))

    def test_invalid_report_templates_have_no_matcher(self):
        cases = [
            self.config("docs/logs/audit_<YYYY-MM-DD>.txt"),
            self.config("docs/logs/audit.md"),
            self.config("docs/<YYYY-MM-DD>.md"),
            self.config("docs/<YYYY-MM-DD>/audit.md"),
            {"docGlobs": ["guide/**/*.md"],
             "reportPath": "docs/logs/audit_<YYYY-MM-DD>.md"},
        ]
        self.assertEqual([self.mod.report_pattern(cfg) for cfg in cases], [None] * len(cases))

    def test_default_enumeration_excludes_only_actual_reports(self):
        write(self.repo, "docs/logs/doc_audit_2026-08-25.md", "report\n")
        write(self.repo, "docs/logs/doc_audit_policy.md", "policy\n")
        out = run(self.repo, "format", self.config())
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["counts"], {"docs": 1, "findings": 0, "fail": 0, "warn": 0})

    def test_default_enumeration_excludes_reports_when_doc_globs_are_omitted(self):
        write(self.repo, "docs/logs/doc_audit_2026-08-25.md", "report\n")
        write(self.repo, "docs/logs/doc_audit_policy.md", "policy\n")
        cfg = {"reportPath": "docs/logs/doc_audit_<YYYY-MM-DD>[_NN].md"}
        out = run(self.repo, "format", cfg)
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["counts"], {"docs": 1, "findings": 0, "fail": 0, "warn": 0})

    def test_explicit_report_path_is_not_excluded(self):
        report = "docs/logs/doc_audit_2026-08-25.md"
        write(self.repo, report, "intro\n[broken](./gone.md)\n")
        out = run(self.repo, "format", self.config(), paths=[report])
        self.assertEqual(
            [(f["severity"], f["path"], f["line"]) for f in out["findings"]],
            [("FAIL", report, 2)])
        self.assertEqual(out["counts"], {"docs": 1, "findings": 1, "fail": 1, "warn": 0})

    def test_explicit_report_outgoing_link_prevents_false_orphan(self):
        report = "docs/logs/doc_audit_2026-08-25.md"
        target = "docs/target.md"
        cfg = self.config(indexFiles=[report])
        write(self.repo, report, "[target](../target.md)\n")
        write(self.repo, target, "target\n")
        out = run(self.repo, "semantic", cfg, paths=[report, target])
        self.assertEqual(out["findings"], [])
        self.assertEqual(out["counts"], {"docs": 2, "findings": 0, "fail": 0, "warn": 0})

    def test_opt_in_true_restores_reports_and_invalid_types_warn_but_exclude(self):
        report = "docs/logs/doc_audit_2026-08-25.md"
        write(self.repo, report, "report\n")
        opted_in = run(self.repo, "format", self.config(auditReportsInCorpus=True))
        self.assertEqual(opted_in["counts"], {"docs": 1, "findings": 0, "fail": 0, "warn": 0})
        for value in ("true", 1, []):
            with self.subTest(value=value):
                out = run(self.repo, "format", self.config(auditReportsInCorpus=value))
                self.assertEqual(out["counts"], {"docs": 0, "findings": 1, "fail": 0, "warn": 1})
                self.assertEqual(
                    [(f["severity"], f["path"], f["line"]) for f in out["findings"]],
                    [("WARN", "(config)", 1)])

    def test_report_exclusion_keeps_text_pass_and_counts_aligned(self):
        write(self.repo, "docs/logs/doc_audit_2026-08-25.md", "report\n")
        write(self.repo, "docs/kept.md", "kept\n")
        output = run_text(self.repo, "format", self.config())
        self.assertIn("SUMMARY pass=1 warn=0 fail=0", output)


if __name__ == "__main__":
    unittest.main()
