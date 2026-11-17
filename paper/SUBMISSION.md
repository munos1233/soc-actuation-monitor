# ACM TOPS submission checklist

This file is the administrative freeze for the manuscript. Scientific numbers
live in `eval/results/latest.json` and `paper/main.tex`.

## Venue and portal

- Journal: ACM Transactions on Privacy and Security (TOPS)
- Portal: https://mc.manuscriptcentral.com/TOPS
- Official page cap: the current [ACM TOPS Author Guidelines](https://dl.acm.org/journal/tops/author-guidelines)
  on the Digital Library are **35 pages TOTAL**. Over that is a desk reject.
- The still-hosted TISSEC author page
  (https://www.tissec.hosting.acm.org/content/process/information-for-authors/)
  still states a **30-page TOTAL** rule. That page is leftover hosting, not the
  live TOPS cap. Do not compress the manuscript to 30 to satisfy it.
- Local gate: `make paper-pages` fails above **35 manuscript pages**
  (`acmart acmsmall,manuscript`). Keep the freeze in the low thirties so a
  table can grow without a second cut.

## Exclusive submission

The manuscript is not under review elsewhere and will not be submitted
elsewhere while TOPS is considering it. Cover letter restates this.

## Prior disclosure

This line of work has not appeared in a conference or journal. There is no
prior rejection to disclose. If that changes, update the cover letter before
upload — TOPS requires full disclosure of prior publication, prior rejection,
and current submission of the same line of work.

## Author set

The author set is frozen at submission. ACM TOPS does not allow adding or
removing authors after upload without the Editor-in-Chief.

## Generative AI (Manuscript Central checkbox)

The language-model planner arm treats a model as an experimental object, not
as an author. Tick the ACM generative-AI disclosure on the submission form
to match the camera-ready sentence already in the manuscript. Evaluation
numbers are not a generative-AI authorship use.

## Artifact

```bash
make paper-pages          # rebuild PDF and enforce the 35-page gate
scripts/pack_paper_artifact.sh
```

The zip contains the PDF, this checklist's sibling cover letter, REPRODUCE.md,
the eval harness, frozen matrices, the model checker (`TEI.tla`,
`TEIPair.tla`, `view_lemma.md`, `scripts/fetch_tlc.sh` + sha256; the
jar is fetched, not zipped), sanitized TLC logs, and an anonymized
backend slice sufficient to drive the production service chain. It does not
contain frontend code, vendor contracts, credentials, or product demo matrices.

`artifacts/dynamic-eval-matrix/` is a different suite. Do not ship it as paper
evidence.

## Data availability

- Main ablation: offline, three Make targets in REPRODUCE.md. The
  anonymous zip has no Compose; REPRODUCE.md also lists the equivalent
  `python eval/harness/run_suite.py` command.
- Mixed-load backlog, coverage search, planner-only process probe, TEI.tla
  (including AttributeOnly, TEIPair / view lemma, Java TLC on three
  configs), kind C5, fixture 22 CI, 2^4 live lattice,
  held-out, playbook-semantic closer, spec-trace replay,
  independent-author dual track:
  `make paper-eval-backlog`, `make paper-eval-search`,
  `make paper-eval-process-split`, `make paper-eval-tla`,
  `make paper-eval-k8s-kind`, `make paper-eval-k8s`,
  `make paper-eval-lattice`, `make paper-eval-heldout`,
  `make paper-eval-independent`,
  `make paper-eval-playbook-semantic`, `make paper-eval-replay`.
  Repeat-run noise (`make paper-eval-repeat`) is artifact-only, not a
  body claim. Appendix B grids are `paper/appendix-b-grids.md`.
  Sampling protocol and `external_sample.json` ship in `eval/taxonomy/`.
  Held-out, kind, and independent-author rows are never pooled with the
  57; kind/held-out are mapped instantiations, not reproductions
  on the original product. Java TLC on the finite slice is not a proof
  of the implementation.
- Language-model planner arms: five arms from four model families
  (`glm-5.3`, `glm-5.3-flash`, `deepseek-flash`, `kimi-k3`,
  `claude-opus-5`) as an existence check, not a model evaluation. The
  reproducer supplies OpenAI-compatible endpoints. Credentials are not in
  the archive. Frozen per-arm outputs ship in `eval/results/planner_arm*/`
  with endpoint identifiers and freeze dates in each arm's README.
- Eval-only database passwords (`planner_role`, `actuation_role`) are for the
  isolated Compose project. A deployment must rotate them.

## What must be true before upload

1. `eval/results/latest.json` matches every headline number in the abstract.
2. `grep -R -E 'ShadowTrace|深信服|张家口|揭榜'` over the staged artifact is empty.
3. Role migrations 0040–0045 are applied on the eval database used to freeze
   the matrix. Eval-only passwords must stay out of production DSNs.
4. The author set, exclusive-submission sentence, and prior-disclosure sentence
   in `cover-letter.md` are still accurate.
5. Suggested reviewers in `suggested-reviewers.md` have been re-checked on
   faculty pages (affiliations move; do not invent addresses).
