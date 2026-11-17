# Cover letter — ACM Transactions on Privacy and Security

**Manuscript:** *Attribute Admission Is Incomplete for Transactional Evidence*

**Type:** Research article (anonymous review)

**Portal:** https://mc.manuscriptcentral.com/TOPS

Dear Editors,

Please consider this manuscript for ACM TOPS. It is not under review at any
other journal or conference, and we will not submit it elsewhere while TOPS is
considering it.

**Exclusive submission.** This manuscript is submitted solely to ACM TOPS. It
is not under consideration elsewhere, and we are not in discussion with another
editor about this line of work.

**Prior disclosure.** This line of work has not been published in a conference
or journal and has not been previously rejected. There is no overlapping
submission.

**Author set.** The authors named in the non-anonymous record are the complete
set. We will not add or remove authors during review.

**Contribution.** Clark--Wilson's IVP assumes a store view. Deploying that IVP
as any function of request attributes---including HMAC-signed attributes and
attached approval copies---cannot decide close or bind (Lemma 1). An OPA
sidecar at the same four decision points leaves a 16/45 residual; a kind
attribute arm leaves 9/11 (naive 11/11, TEI webhook 0/11). The SOC
construction is 49/57 naive versus 0/57 full on an author-constructed suite.
Kind and held-out rows are mapped instantiations on our object model.

An independent-author dual track is reported as two separate lines under
a blindness-bound brief. A co-verification layer archives an independent
table re-execution protocol (R1; cell-diff totals at joint freeze),
source review of the four gates (G1/G2), and CVE-mapping fidelity on the
kind eleven (K1/K2). Those layers are reported separately from the 57.

**Threat model.** Host root and a stolen actuation login are outside the
model. The default deployment is two OS processes: the planner process is not
given the writer factory, and planner SQL on the privileged columns is
refused (SQLSTATE 42501).

**Evaluation.** The main table is boundary injection through the production
service chain. Harm is scored from database and vendor facts, not from a gate
return value. Adversary A0 issues the privileged writes as the planner login,
from a planner-only child process. PostgreSQL refuses them; the same
statements succeed as the owner login.

**Suggested assignment.** Please route this manuscript to systems-security and
access-control reviewers. The primary contribution is an interface lemma for
attribute-shaped admission on write paths, instantiated on tickets and a kind
lab cluster. Researchers in workflow / change-advisory integrity and
empirical SOAR studies are also appropriate. LLM-agent reviewers are welcome
as a complement, not as the only pool.

**Data availability.** The ablation matrix, case registry, invariant checkers,
sampling protocol, external sample, kind manifests/webhook, and an anonymized
source slice ship with the anonymous artifact. The language-model planner arm
needs an OpenAI-compatible endpoint supplied by the reproducer; credentials
are not in the archive. Eval-only role passwords in the migrations are for the
isolated Compose project and must be rotated in any deployment.

Thank you for your consideration.

Anonymous Author(s)
