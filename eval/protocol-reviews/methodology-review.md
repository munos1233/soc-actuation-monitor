# Protocol review 1 — adversarial methodology review (agent, 2026-09-16)

Role: skeptical TOPS methodology reviewer, run before arbiter approval
of `eval/protocol-independent.md` v1 draft. Findings below are archived
verbatim (Chinese, as returned). All twelve findings were incorporated
into protocol v2:

- BLOCKER ×3 → §10.3 (arbiter-only malformed declaration), §6 Gate C
  (structural wording, no class signatures), §5 R6 + §14 (query-space
  bound stated, non-security queries added).
- MAJOR ×6 → §3 (frozen role prompts + sanitized grid), header (freeze
  evidence options + §14 honesty clause), §11 (full re-run + per-row
  commit hash, mixed-version tables forbidden), §5 (cap justified as
  labor bound, R2/R4 execution defined), §10.1 (idle computed from the
  naive arm alone), §13 (pre-registered outcome interpretations).
- MINOR ×3 → §2 (17-config excluded, not "optional"), §3/§4 (arbiter
  review after freeze + arbiter_log.md), §8/§12 (predicate_mapping
  field).

Verdict of the reviewer on v1: "不接受当前版本" with the noted fix list;
v2 implements every fix.

---

## 原文（verbatim）

**1. [BLOCKER] §10.2 — "malformed by construction" 是无限的后门。**
"drives nothing, races the wrong layer" 的判定标准完全主观，且是在看到结果后由与论文作者同属一人的操作者（implementer agent）做出的。一个 full 配置下产生 harm 的 case，可以被宣布为 "races the wrong layer"（认定有误），"fixed once"（修复一次），然后重新跑。修复（"fix"）本身可以改变 case 的语义。"fixed once" 的限制形同虚设——每个 case 可以被认定一次 "malformed"（格式错误），修复一次，但如果修复后结果仍不理想，可以再认定一个不同的 bug。**修复建议：** 删除该例外，或将 "malformed" 的判定权交给 arbiter（仲裁人）且要求在修复前用书面理由证明 case 在任何配置下都不可能产生有效信号（而非仅仅产生不理想的结果）。修复后的 case 必须标注为 "v2" 并在正文中同时报告原始结果。

**2. [BLOCKER] §6 — "syntactic filter" 的措辞内嵌了 T1–T8 签名。**
Include 条件 2 列出："a confused deputy, a weak receipt treated as confirmation, an observation used as a write, a dual dispatch, or a privileged login on the proposer's seat" —— 这分别是 T1、T5、T6、T7、T8。协议声称 "does not judge […] mappability"（不判断可映射性），但过滤器的字面文本枚举了已发表分类的模式。一个不符合任何 T 类签名的 item（即 T9 候选）会在过滤器层被排除，因为审阅者找不到对应的枚举关键词。**修复建议：** 将 Include 条件 2 改为纯粹的句法描述（"the source describes an event where a persistent write-protected record was modified or created"），删除所有与 T 类对应的枚举示例，或将示例移至非规范性脚注。

**3. [BLOCKER] §5 — 查询集在 "no refinement"（不优化）的表象下预烘焙（pre-bake）了结果。**
R1–R5 的所有查询都瞄准 SOC/ITSM/SOAR 词汇——即实现的表达面。没有查询瞄准可能产生 object-model-boundary 或 T9 发现的领域（例如非安全自动化完整性故障、企业工作流数据损坏、非 SOC 票务系统）。"No iterative refinement" 是一个优点，但它使查询集成为唯一的防线——而这个查询集由已知实现能表达什么的人选择。**修复建议：** 添加至少 3 个明确不针对 SOC 词汇的查询（例如 "database record integrity violation automation"、"enterprise workflow unauthorized state change"、"business logic integrity bug production incident"），或者明确承认该 suite 只能回答 "查询集定义的空间内" 的构建问题。

**4. [MAJOR] §3/§13 — "prompt-level role separation" 不可审计、不可验证。**
Constructor agent 的 "Must not see" 列表是理想化的。没有任何机制验证 agent 的上下文中确实不包含 `cases.py` 或 `chain.py` 的知识。Timestamps 证明输出顺序，不证明输入隔离。同一操作者可以在 prompt 中泄露实现的形状（例如 "you may not use gate names like close/bind/verify/egress" —— 这句话本身就告诉了 constructor 四个 mediator 的名字！）。**修复建议：** 发布每个 role 的完整 prompt 到 artifact 中作为 freeze 的一部分；将 "Must not see" 列表中的禁词（如 mediator 名）从 prompt 本身中移除；或者引入外部时间戳服务（如 timestamp authority）。

**5. [MAJOR] §12 — freeze timestamps 可被伪造。**
Git commit 时间可以任意设置。"Freeze reference" 是一个 self-attested（自证）的 hash。一个 bad-faith 作者可以在 Phase 4 之后创建一个 backdate（回溯日期）的 commit。**修复建议：** 在 arbiter 批准时将 protocol hash 提交到外部不可篡改的存储（如公开的 git hosting service 的 dated commit、或 timestamping authority）。

**6. [MAJOR] §11 — "re-run the affected layers" 引入混合版本结果。**
如果一个 case 在 full 下 harm，修复 TEI 构造后 "re-run the affected layers"——但其他 case 可能已经在旧代码上跑过。最终表格中混合了旧代码和新代码的结果，且没有要求标注哪个 case 在哪个版本上运行。**修复建议：** 要求修复后全部 Suite C case 重新运行，或至少在结果中标注每个 cell 对应的代码版本。

**7. [MAJOR] §5 — 12-item cap 无 justification（理由说明），且 R2 的 "executed once" 定义不明。**
v1 用 40，此处用 12，没有解释。R2（vendor PSIRT 页面浏览）中 "executed once" 意味着什么？看第一页？全部页？**修复建议：** 说明 12 的选择依据；为 R2 定义具体的浏览深度（如 "all advisories on the vendor's security advisory index page(s), up to 3 pages deep"）。

**8. [MAJOR] §10.1 — "idle (harm not reachable)" 的判定是 post-hoc（事后）的。**
谁决定 harm 是 "not reachable" 还是 "prevented"？这是实现层面的判断，可被操作。**修复建议：** 定义 "idle" 的客观标准（如 "the precondition for the injection is never triggered because the naive chain produces no actuation attempt"），并在结果中报告判定的具体依据。

**9. [MAJOR] — 缺失：stopping rule（停止规则）/ 空结果处理。**
如果所有 12 个 item 都是 `not_instantiable` 或 `object_model_boundary`，协议支持什么 claim？没有说明。**修复建议：** 预注册每种可能结果的解读（如 "if 0 cases instantiate, the claim is that the object model's expressiveness is the limiting factor, not the construction process"）。

**10. [MINOR] §2 — "seventeen-configuration grid […] optional and may be run later"。**
预注册中的 "optional" 是一个选择性报告的通道。**修复建议：** 要么要求、要么明确排除，不要 "optional"。

**11. [MINOR] §3 — Arbiter 看 everything（所有内容），是不盲的。**
Arbiter 在 Phase 2 review（审查）时可看到实现，可能向 constructor 间接传递实现知识。**修复建议：** 限制 arbiter 在 Phase 2 时不看实现代码，或记录 arbiter 的全部反馈。

**12. [MINOR] §8 — predicate 编码无 rubric（规则）。**
"expected harm predicate" 从自然语言翻译为程序化检查时涉及判断，无编码规范。**修复建议：** 要求 implementer 在 case 表中记录 predicate-to-code 映射的具体依据。

**裁定结论：** 不接受当前版本。发现 1、2、3 是根本性缺陷——它们共同允许 bad-faith 作者在 "预注册" 的掩护下通过过滤器措辞、查询集设计和事后 "malformed" 认定来控制结果。发现 4、5 使整个 artifact trail（产物轨迹）在敌意审阅者面前不具证明力。如果这些问题被修复——特别是删除 §10.2 的后门、重写 §6 的句法过滤、在 §5 中加入非 SOC 查询、以及将 freeze 提交到外部可信存储——那么该协议可以支持一个有限但诚实的 claim："在一组预先固定的查询和句法过滤器下，不从实现出发构建的 case 可以被系统性地生成并在生产链上运行"。这个 claim 有价值，但它远弱于 "独立验证"，且任何此类 claim 的措辞必须反映 §13 中已承认的局限性。协议的最大优点是其自我意识——它知道自己不能声称什么；最大的风险是它的规则仍然允许作者在看到结果后改变结果。
