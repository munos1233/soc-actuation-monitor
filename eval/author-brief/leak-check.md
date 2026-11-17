# Brief leak-check (adversarial audit, 2026-09-17)

Auditor: an agent with full repository access (case registry, Injection
knob catalog, gate implementations, paper §2), tasked with finding any
content in the author brief that would channel independent authors
toward existing cases or defenses. Verdict: **issue-after-fixes** — no
case-id or gate-name level leaks, but the harm parentheticals and the
receipt enumeration functioned as case-space leakage for the A1/A4/A5
families, and the async dispatch model was missing (under-supplying A3).

All findings incorporated into `threat-model-brief.md` v1.1 and
`submission-template.md` v1.1 before issue:

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | LEAK | Harm-1 parenthetical enumerated the close gate's internal checklist | parenthetical removed |
| 2 | BORDERLINE | Receipt enumeration mirrored ReceiptProfile values | generalized to "receipts and verification answers of any evidential strength, including false ones" |
| 3 | BORDERLINE | Echo phrase handed over a5_echo_observation | subsumed by #2 |
| 4 | BORDERLINE | Harm-4 parenthetical named the two A4 payload types | "confidential analysis content crosses to the vendor side" |
| 5 | BORDERLINE | Harm-5 parenthetical enumerated the A5/A1 lie family | removed |
| 6 | BORDERLINE | "anchors object identity" implied the locator-witness check | comment removed; plain may-not wording |
| 7 | OK-NOTE | Harm-2 "target, tool, or content" matches mutation values | kept — definitional anchor |
| 9 | BORDERLINE | Combined channeling toward A1/A4/A5, under-supply of A3 | resolved by #2–#5 plus #10 |
| 10 | MISSING | No async/concurrent dispatch model | added to may-list ("dispatch is asynchronous; may be dispatched more than once, including concurrently") |
| 11 | MISSING-light | All-human approval narrowed the space | added "some low-tier actions may be auto-approved" |
| 13 | BORDERLINE | Form fields 4 and 6 duplicative; field-6 framing contaminated independence | field 4 removed; field retitled "Hypothesis: what would a reasonable implementation have to check" |
| 14 | OK-NOTE | Implementer footer visible to authors | moved to protocol §4 |

Audited brief version: v1.0 (pre-issue draft). Issued version: v1.1.
The full auditor report is preserved verbatim below.

---

## 审计报告原文（verbatim）

**1. [LEAK] Harm 1 括号句。** *"no confirmed effect, no report, superseded plan"* —— 这是 close gate 的内部检查清单逐项枚举，1:1 对应 knob（`skip_terminal_action`/receipt profiles、`skip_report`、`bump_revision_after_activation`/`strip_outbox_revision`）。且 "report" 在 brief 全文无定义，属实现内部概念。

**2. [BORDERLINE] may-list 收据枚举。** *"receipts that claim success, receipts flagged as simulated, receipts with only an acknowledgement"* —— 与 `ReceiptProfile` 枚举值（LYING_SUCCESS / SIMULATED_CONFIRM / WEAK_ACK）几乎逐词对应，等于把 a1_simulated_receipt、a1_weak_receipt、a5_lying_vendor_receipt 递到作者手上。虽逐字继承自 paper §2，但在 brief 语境下起的是 case-inventory 作用。

**3. [BORDERLINE] may-list echo 短语。** *"answers to verification queries that merely echo the request back"* —— 即 a5_echo_observation（ECHO_SUCCESS / ECHO_ONLY_DETAILS），且 harm 5 再重复一次 "echo"，双重强化。随第 2 条一并泛化。

**4. [BORDERLINE] Harm 4 括号。** *"(investigation narrative, credentials)"* —— 恰好是 A4 仅有的两个 egress case（a4_narrative_in_target、a4_secret_in_target）的载荷类型。

**5. [BORDERLINE] Harm 5 括号。** *"(an echo, an acknowledgement, or a lie counted as proof)"* —— 枚举了整个 A5/A1 谎报家族。

**6. [BORDERLINE] may-not 的 disposition source 注释。** *"the locator the operator chose, which anchors object identity"* —— "anchors object identity" 是 a0_planner_sql_disposition_source 中 "witness of object identity" 的软回声，暗示存在以 operator locator 为基准的身份核对。

**7. [OK-NOTE] Harm 2 括号** *"(target, tool, or content changed relative to approval)"* —— "target/tool" 与 `mutate_after_approval` 取值相同，但 harm 定义需要锚点，"changed relative to approval" 是定义性的。可接受。

**8. [OK] 以下未越界**：may-list 字段枚举（与 paper 逐字同）；"cause a dispatch to be retried / revise a plan after the human decision"（能力声明）；"inject upstream free text"；"the system is supposed to keep them that way"（仅披露防御存在，by design）；三个 write 的不可互换示例。未泄漏任何 gate 名、mediator 词表或 case id。

**9. [BORDERLINE] 组合效应**：第 2–5 条叠加后，A1/A5（收据形状）和 A4（narrative/credential）被过度引导，作者产出将是 retag；A3 反而供给不足。

**10. [MISSING] 异步/并发模型**。作者不知道 dispatch 经由异步 worker，就不太可能想出并发双发类攻击。补充："Dispatch to the vendor is asynchronous; the same approved action may be dispatched more than once, including concurrently."

**11. [MISSING-light] 自动批准层级**。brief 写成一律人工批准，收窄了设计空间。加 "some low-tier actions may be auto-approved"。

**12. [OK-NOTE] "terminal disposition"** 对 SOC/K8s 工程师可映射，三 writes 的不可互换示例已足够。may/may-not 拆分无歧义。

**13. [BORDERLINE] 字段 4 与 6 重复**且都诱导防御猜测；字段 6 标题预设作者建模真实防御，与 brief "no advantage in guessing" 自相矛盾。删字段 4，字段 6 改题。

**14. [OK-NOTE] 页脚** *"knob mapping, executable case id"* 对作者可见，暴露存在 knob 词表。移入实现方文档。

**结论：issue-after-fixes。** 无 case id / gate 名级硬泄漏，但 harm 括号与收据枚举实质构成 A1/A4/A5 的 case-space 泄漏，且缺异步模型说明。修 1–6、10、13 后可发布（约 8 处文字改动，无需重写）。
