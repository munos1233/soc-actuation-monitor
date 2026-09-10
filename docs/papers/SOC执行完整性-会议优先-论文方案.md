# 论文方案：不可信 planner 下的 SOC 执行完整性（会议优先）

> 取代此前的《ACM TOPS 论文方案：SOC 执行路径上的参考监控器》。
> 变更依据：TOPS 首轮标准下，「十条性质 + 同进程 TCB + 对谓词做开关消融」的框架即使把用例扩到 100 条也没有实质机会。结论是 **B：先会后刊**。本文档按收缩后的四门重写。
>
> 与旧版的三处硬性差别：
> 1. **不再自称 reference monitor。** 中介函数与 planner 同进程，Anderson 的防篡改一条我们做不到，标题与摘要都不许暗示做到了。
> 2. **贡献收缩为四条可关中介**，P5/P8/P9/P10 降为实现机制，不进贡献句、不做假开关。
> 3. **评测主表只报边界注入**，门函数返回值的真值表退到附录，并明确写「这不是中介证据」。

---

## 0. 一页决策

- **目标会场：** ACSAC（`acmart sigconf`，双盲）为第一志愿，DSN Regular（IEEEtran，故障注入 / fail-open vs fail-closed 叙事）为并列备选。会议与期刊互斥，先会。
- **标题（工作稿）：** *Evidence-Gated Actuation: Fail-Closed Ticket Closure and Dispatch under an Untrusted Planner*。
- **一句话贡献：** 不可信 planner 只许提案；工单 CLOSED、动作下发、效果认定与出站载荷这四个决策由 planner 未曾书写的证据计算，且这一点要用边界注入而不是门函数单测来证明。
- **不写的东西：** 保护域、密码学、检索/多智能体、越狱防御、`force_close` 当关单、mock 回执当 live 确认。
- **再冲期刊的前提：** 会议录用后拿到实质增量（真保护域或跨进程唯一写路径、独立红队攻击集、可复用的 actuation-integrity 模型），而不是把 11 页拉成 35 页。

---

## 1. 定位

审稿人池要么来自 LLM-for-security，要么来自 dependability。两边的差别句都要一句话说清：

- 对 LLM-SOC 一侧：他们评的是分析质量（分诊准确率、根因一致性）。我们评的是世界状态与关单记录，分析质量不在指标里。
- 对 SOAR / dependability 一侧：他们把剧本语义当真（剧本说containment 跑过了就可以关单）。我们把关单当成需要证据的谓词，证据不能由提案方书写。

**不许出现的定位句：** 「我们把参考监控器搬到了 SOC」。这句话会直接把审稿池换成 Anderson/完整中介的人，而我们的中介是同进程 Python 函数、环境变量可卸载。

---

## 2. 三条贡献

### C1 — 四条被中介的决策（性质数 = 中介数）

| 门 | 性质 | 对手 | 危害 | 代表错误码 |
| --- | --- | --- | --- | --- |
| 关单门 | 进入 CLOSED 需收敛证据；未知策略即拒；required 时需强回执且非 simulated | A1 无功关单 | wrong-close | `closed_requires_report` / `closed_side_effects_pending` / `closed_weak_confirmation_evidence` / `closed_simulated_receipt_rejected` |
| 绑定再审 | 下发内容必须等于被批准的内容（内容重算，不比对 planner 自己写的列） | A2 签后漂移 | wrong-act | `action_content_drift` / `plan_revision_mismatch` / `playbook_binding_mismatch` |
| 观察/执行分离 | 观察效果不得产生效果；SUCCESS 无 `is_verified` 是 unverifiable | A5 无功认定 | false-verify | Phase 1 不得激活终态；deferred 是 skipped 不是 failed |
| 出站白名单 | 出站载荷限于按 intent 的字段白名单，且必须指向事件已选定的处置对象 | A4 分析出站 | leak | `no_analysis_content_outbound` / `disposition_field_allowlist` / `disposition_source_match` / `outbound_guard_internal_error` |

**退出贡献句的四条（正文写成实现机制，附录给细节）：**

- P5 至多一个活跃终态头 → 部分唯一索引 + 投递时活跃头断言。**没有可关开关，也不许造一个。**
- P10 单一执行者、P8 字段写者权威、P9 义务 ⊥ 能力 → 工作内存/字段所有权工程。

### C2 — 中介与唯一写路径

四门的检查、错误码，加上一条路径论证：对每个外部效果，从不可信提案到该效果的每一条边、谁是唯一写者、剩下什么仍被信任。图 1 是**生产** TCB 图，**不得**出现 eval 开关。

### C3 — 边界注入评测

注入点在系统边界（planner 写的行、厂商回执、厂商对核验查询的回答、重复下发），经未改动的服务链跑真 PostgreSQL 与厂商 stub，危害从数据库与厂商侧事实判定，不看门函数返回值。报 leave-one-out、同配置金路径（含 overblock）、无 planner 基线、mock 与伪 live 分列。

---

## 3. 威胁模型

**对手在数据平面。** 能写：工具名、目标、参数、级别、执行者、source locator、fingerprint 标签、模板哈希、剧本引用。能供：声称成功的回执、simulated 回执、只有 acknowledged 的回执、回声式核验答案。能做：重复下发、人工批准后改计划。

**对手不能：** 在中介内执行代码、设置服务进程环境变量、直接写状态列或批准记录（把动作推进 `APPROVED` 是状态迁移，不是计划内容，由状态机校验把守）。管理员 `force_close` 是声明的绕过，出模型，且永不计为关单。

这些排除必须写进正文——它们是评测可解释的前提。

---

## 4. TCB（正文 §3，先于设计）

- **界外：** planner 输出与 prompt、检索上下文、工具返回与执行器回声、报告正文与决策轨迹、编排 checkpoint 自报、UI 文案、厂商回执字段。
- **界内：** 四门；outbox worker（厂商命令的唯一写者）；终态头与动作 claim 的数据库约束；批准记录；安装这些约束的迁移。
- **被信任但未被中介：** 进程边界本身。四门是 planner 进程可以调用的函数，不是保护域；`EVAL_DISABLE_*` 只为消融存在，不进生产边界。单独设置任一开关会在 `Settings` 构造时被拒（必须同时 `EVAL_HARNESS_MODE=true`），因此误配的进程起不来——这是防误操作，不是防篡改，正文必须这样写。

---

## 5. 评测（已在仓库实现）

代码位置：`backend/app/eval_suite/`（`chain.py` 驱动、`cases.py` 用例登记、`gold.py` 套 A、`runner.py` 汇总、`component.py` 附录检查），CLI 为 `eval/harness/run_suite.py`，结果写入 `eval/results/`。

- **套 B（主表）：** A1–A5 边界注入，经真实调用链。A3 走 outbox 并发/双 worker，A5 实例化真的 VerifyAgent。**A2 里没有「谁都没批准就下发」这一条** ——那要求改状态列，出威胁模型，已在 `cases.py` 写明原因。
- **配置：** naive / close_only / bind_only / verify_only / egress_only / full，加 full−close、full−bind、full−verify、full−egress 四档 leave-one-out。
- **两列厂商：** mock（`mock_xdr` + mock 适配器 + 禁写回）与 pseudo_live（`pseudo_live_xdr` + http 适配器 + 允许写回，可谎报 SUCCESS、丢回读、只给 acknowledged）。禁止用 `disposition_is_mock=false` 冒充 live。
- **基线：** dead_playbook（同样的动作、无自适应 planner），用来说明危害不是「没有剧本」。
- **套 A：** 与套 B 完全同一 Full 配置，报 CLOSED 率、over-block、额外人工介入、额外 worker 轮次。`force_close` 在套 A 里是禁用的（`gold.py::FORCE_CLOSE_FORBIDDEN`），金路径失败就是失败。
- **诚实项（必须单列一小节）：** 在所有可关中介全关的 naive 配置下危害仍为 0 的用例要单独报告并解释（A3 由数据库层中介；mock 列的弱回执按设计可关单）。这一列是自证伪记录，不是成绩。

**方法学产出（写进正文，不要藏在致谢里）：** 边界注入暴露了两条谓词单测看不见的 fail-open，两处都是生产修复：

1. 绑定再审比对的是 planner 自己写的 `action_fingerprint` 列（自证），改为按下发内容重算指纹。
2. 出站卫士把命令自带的 locator 当作对象身份的见证（自证），改为以事件上由操作员选定的 `disposition_source_ref` 为见证。

**仪器自身的一处修复：** 厂商桩原先把一次投递重试算作第二次外部效果，A3 因此在 1/3 上抖动。桩现在遵守它自己声明的 `supports_idempotency` 语义（同一幂等键折叠到首次回执），`delivered_intents` 按幂等键计不同效果，并新增 `a3_idempotency_key_rewrite`（planner 改写幂等键——它不在指纹 11 段里）验证这条路仍被单次认领挡住。

---

## 6. 相关工作分组（每组一段 + 一句差别）

1. **控制平面 admission：** Kubernetes admission webhook、OPA/Gatekeeper、云 IAM 条件键。差别：客体是工单 CLOSED 与厂商强回执，不是 API 对象 schema。
2. **Agent 工具 TCB：** CaMeL、dual-LLM 模式、IsolateGPT、AgentDojo。差别：我们中介的是 SOC 世界状态与回执真实性，不是工具进程隔离；我们不声称防越狱。
3. **SOAR / ITSM 审批与幂等：** XSOAR 审批任务、剧本版本化、幂等键。差别：不把 planner 与工具回声当语义真值。
4. **两阶段提交与回执：** prepare-commit 与「观察 ≠ 执行」的关系。差别：这是安全属性而非可用性属性，且对手会伪造 prepare 的证据。
5. **LLM-SOC 评测：** 分诊/根因类 benchmark。差别：他们评分析质量，我们评世界状态；两者指标不能混表。

工业 GitHub 项目不作主对照。

---

## 7. 状态清单

| 项 | 状态 |
| --- | --- |
| 四门实现与错误码 | 已在生产代码 |
| 边界注入套 B + LOO + 两列 + dead-playbook 基线 | 已实现，结果落 `eval/results/` |
| 套 A（金路径 + overblock，禁 force_close） | 已实现 |
| 谓词级检查降为附录 | 已完成（`component.py` 顶注写明不是中介证据） |
| 两条 fail-open 生产修复 | 已合入，回归零净新增失败 |
| `paper/main.tex` 四门重写 | 已完成，含评测数字、路径论证、相关工作，编译 6 页无错 |
| `references.bib` 近邻密度 | 已补 20 条，五组各有差别句 |
| 生产 TCB 图（不含 eval 开关） | 已画（`fig:tcb`，只有生产写路径与数据库约束） |
| 打分器正控 | 已加（`tests/eval/test_monitor_pilot.py`），五类危害各有一条「构造即危害」的用例 |
| 真 LLM 金路径墙钟 | 未做，不在本轮声称 |
| 形式化 | 不做，也不声称 |

### 定稿数字（`eval/results/latest.json`，2026-09-10）

| 项 | 结果 |
| --- | --- |
| 套 B naive → full | mock 16/21 → 1/21；pseudo_live 17/22 → 0/22；合计 33/43 → 1/43 |
| leave-one-out 边际 | close +14、bind +8、egress +4、verify +3（基数 43） |
| full 下仍可达的危害 | 1 条：`a1_weak_receipt`（mock 列按设计不算确认；同一用例在 pseudo_live 被 `closed_simulated_receipt_rejected` 拒） |
| 单门归因 | `egress_only` 只挡 A4；`bind_only` 挡 A2 并顺带挡 `a4_locator_swap`（locator 在指纹 11 段里，属纵深而非度量瑕疵） |
| 非单调性 | 卸掉 verify 反而掩盖 `a1_weak_receipt`（deferred 记失败 → 动作到不了可关状态），正文写成「一个中介可以靠更早失败掩盖另一个中介的失败」 |
| 全配置为零的列 | A3 全 0（数据库层：终态头部分唯一索引 + 单次认领 `invalid_state_transition`）；`a2_level_downgrade` 在 naive 也被审批等级校验挡下。两者都不归功于四门 |
| dead-playbook 基线 | 43 中 10 条按构造不适用（已单列脚注排除）；余下 naive 17/23 → full 1/23 |
| 套 A（Full） | 两列各 4/4 CLOSED、0 over-block、0 人工、2 次额外 worker 轮次，`force_close` 未用 |
| 套 A（naive 对照） | 也 4/4 CLOSED，但需 4 次人工处置 → 四门不花关单率，反而减少人工 |
