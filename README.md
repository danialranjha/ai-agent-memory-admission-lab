# AI-agent memory admission: one large record can stop the scan

This offline research experiment runs the **actual formatting body** from Vivvy at commit `b5679309d4e072d34d7ac1456426c51361970002` on supplied synthetic recall records. It compares the unchanged body with one proposed change: when a record does not fit, `continue` to the next record instead of `break` out of the loop.

For the chosen first-record witness, the original returns `""`; the proposed variant returns `"KEEP-A\nKEEP-B\n"`. Both omit the oversized record. No model, memory database, retrieval engine, real endpoint or secret is involved. This is a formatter-component reproduction, not a complete Vivvy run or a released upstream patch.

## Hypothesis and threat model

A record too large for the remaining context allowance can suppress later small records because the formatter stops traversing the list. Continuing the traversal should preserve later records that fit under the same estimate.

Assume an attacker can influence the size of one stored memory **and that it appears before useful records in the supplied recall order**. This harness does not demonstrate insertion or retrieval rank manipulation. The supplied order, formatting options and test program are trusted. The measurable boundary is the returned context string, not model behavior, authorization or task completion.

## Reproduce

Requires Python3.10+ and `rustc` with Rust2021 support. Tested with Python3.13.5 and rustc1.97.1. No Python packages, Cargo dependencies or downloads are needed for the run. Compilation uses a temporary directory that is removed after execution.

```sh
python3 experiment.py
python3 -m unittest -v test_experiment
python3 run_checks.py
```

The first command regenerates [artifacts/run.json](artifacts/run.json) and [evidence.md](evidence.md). The last records the normal suite and two deliberately broken variants in [tests.json](artifacts/tests.json) and [mutations.json](artifacts/mutations.json). Tests do not call a model or network service.

## Technical walkthrough

[Upstream issue16](https://github.com/one2seven-oss/vivvy/issues/16) describes three formatter concerns. This experiment selects only **early termination of budget admission**. It does not test the issue's prompt-injection or template-substitution claims, nor inherit its token-count assertions.

The actual [source function](https://github.com/one2seven-oss/vivvy/blob/b5679309d4e072d34d7ac1456426c51361970002/ltm/src/lib.rs#L485) estimates units as `ceil(UTF-8 byte length / 4)` using Rust `f32`. These are not measured model tokens. It formats a line, estimates that line, and stops when the line would exceed the remaining allowance. Newline bytes appended afterward are not included in the line charge.

The paired witness uses the valid custom template `{content}`, no header/footer and a budget of8 estimated units. Recall records are already supplied, in this order:

1. 48 `L` characters: estimated cost12.
2. `KEEP-A`: estimated cost2.
3. `KEEP-B`: estimated cost2.

**Stop at first unfit record (unchanged):** the first record needs12 and only8 are available, so the loop ends. Exact output is the empty string.

**Continue after unfit record (proposed):** the first record is skipped, leaving8 available. Both short records are emitted, in order. Exact output is `KEEP-A\nKEEP-B\n` (14 UTF-8 bytes). The large record is still absent; nothing truncates or summarizes it.

The ordinary twin, containing just the two short records, returns the same bytes in both variants. Moving the large record last also preserves both small records in both variants. Placing it in the middle leaves only the first small record under the original and both under continuation.

The proposed change is exactly one branch:

```diff
 if current_token_estimate + line_tokens > options.max_tokens {
-    break;
+    continue;
 }
```

All formatting and estimation behavior otherwise stays the same. [Source provenance](vendor/source.json) records the original file's commit, Git blob, SHA256, slice lines and local hashes. [formatter_body.rs](vendor/formatter_body.rs) preserves lines492–531; [estimate.rs](vendor/estimate.rs) preserves lines562–567. The runner verifies these hashes before compiling. `harness.rs` supplies minimal structs, `Fact` kind, score0.5 and fixed records; the original `recall` call and storage stack do not execute. The upstream positive-budget validation is mirrored at the wrapper boundary. Every declared fixture uses valid options.

## Results and checks

Fifteen fixtures produced 30 exact input/method rows. Six pairs changed. The other nine stayed byte-identical. [The complete scenario table](evidence.md) includes first/middle/last order, ordinary and exact-fill twins, no remaining space, empty/all-large lists, headers, footer, Unicode and the upstream default template/header.

Twelve focused tests passed. An independent integer-chunk admission calculation checked all 1,728 combinations of three lengths from `[0,1,4,5,8,12]` and eight positive budgets, across both methods (3,456 strings). This finite calculation is a check on the tested small-input behavior, not a general proof or sample of real memory traffic.

Restoring the early stop caused 6 test failures. Admitting overflowing records caused 8. Both deliberately broken variants were detected. Exact output bytes are the primary oracle. The fixture-ID summary uses unique, non-empty marker strings; empty records use exact bytes, not substring IDs.

## Limits that remain

- **This does not prove model forgetting or successful memory poisoning.** It establishes missing text at the formatter's output boundary, conditional on the supplied order.
- **Continuation is a greedy scan, not optimal selection.** Earlier fitting records can still consume all room. It does not ensure relevance, fairness or resilience to many small unwanted records. If records depend on each other, silently dropping one may be unsuitable.
- **The budget estimate is not a hard bound.** An oversized header is emitted anyway. Two four-byte records at budget2 produce 10 output bytes after newlines; whole-output `ceil(bytes/4)` is 3. Five empty records at budget1 produce five newline bytes. These behaviors appear in both variants and are not fixed by this change.
- **No actual model tokenizer was used.** Unicode is charged by UTF-8 bytes in the original estimator. Its correspondence with any particular tokenizer is untested. Large-input floating-point precision is outside this small-input experiment.
- **Storage, recall ranking, validation integration and downstream task quality are untested.** No entire library service or installed package was run. A production adoption needs a deliberate omission policy, input-size and recall-work bounds, and full-context accounting with the actual downstream tokenizer if a hard token limit is required.

For an ordered best-effort context assembler, decide explicitly whether one unfit record should end the scan. If later fitting records should survive, skip that record and continue; test the exact resulting context and a normal all-fitting case. Check hard context limits separately.

## Attribution and modifications

Source slices are from **Vivvy, The Vivvy Authors**, at the pinned commit above, under the supplied [Business Source License](vendor/LICENSE). This is non-production development/research use. Original source slices are unchanged. The runner generates a derivative with the documented one-branch modification; wrappers, fixtures, tests and reports are added research harness code. The included license and attribution must be preserved when redistributing these slices. No upstream endorsement or production suitability is implied.
