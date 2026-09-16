# Protocol review 2 — constructor-simulation review (agent, 2026-09-16)

Role: the agent that will execute the Constructor role, reviewing the
protocol v1 draft as its only instruction manual before starting.
Findings archived verbatim (Chinese, as returned). All thirteen
execution findings were incorporated into protocol v2:

- #1/#2/#3 (queries not executable) → §5 rewritten as frozen
  engine + exact string + depth triples (50 results / 3 pages; R2 index
  URLs + hit terms; R4 single library named).
- #4 (cap tie-break, advisory_date) → §5: published date, ties by id.
- #5 (hidden reference to sampling.md) → §6 gates fully inlined.
- #6 (write-object gate ordering) → Gate B is now the hard gate,
  checked before the event shape; out-of-scope items logged.
- #7 (duplicate primary) → priority order defined.
- #8 (vocabulary self-contradiction) → sanitized grid created
  (`taxonomy-grid-public.md`), §7 vocabulary rule references only it;
  protocol text contains no mediator names (grep-verified).
- #9 (quote rigidity) → ≤2 sentences / 40 words; open-abstract rule.
- #10 (narrative completeness) → required elements (a)–(e), one
  arbiter-return cycle.
- #11 (missing schema fields) → `mapped_class`, `t9_reasoning` added.
- #12 (freeze-layer mechanics) → append-only semantics + per-phase
  timestamps.
- #13 (T9 timing) → adjudicated inside the Phase-2 arbiter gate.

Reviewer's refusal conditions on v1 (top 3: vocabulary contradiction,
retrieval executability, schema gaps) are all resolved in v2.

---

## 原文（verbatim）

**1. §5 R2 根本不是可执行的查询。** 引文："Splunk (SOAR) security advisories: automation / playbook / action"。这是描述，不是查询串。在哪搜（Splunk PSIRT 页面？Google？site: 限定？）、什么算命中（标题含 playbook？正文含 automation？），两个执行者会得出完全不同的结果集。**需要**：把 R2 每条改写为「引擎 + 精确查询串 + 命中判据」三元组。

**2. §5 "executed once" 对 R4 不可判定。** 引文："Search (Google Scholar / ACM DL / IEEE)"。三个库各跑一次（9 次执行）还是总共一次？在哪个库？各库排序不同、Scholar 有反爬限制。**需要**：明确每个查询 × 每个库各一次，或指定单一库。

**3. §5 无结果深度规则。** NVD 返回 500 条时翻几页？零结果时（R3 的 `automated runbook wrong target incident report` 很可能为零）"finds nothing" 够了，但 500 条时前 20 和前 200 是不同样本。**需要**：固定翻页深度（如「按相关性取前 N=50，逐条过 §6 过滤」）。

**4. §5 cap 无并列规则。** 引文："keep the earliest 12 by advisory_date"。同日多条时如何取舍？且 NVD 有 published 与 modified 两个日期，`advisory_date` 取哪个未定义。**需要**：tie-break 规则（如同日按 id 字典序）+ 日期字段定义。

**5. §6 引用了我看不到的文件。** 引文："as in the v1 protocol (sampling.md)"。§3 规定 Retriever 只能看 §5 查询和 T1–T8 网格；Constructor 只能看主源、网格、本协议。但 §6 的排除规则援引 sampling.md——两个角色都无权读它。**需要**：把相关排除规则内联进本协议。

**6. §6「syntactic only」名不副实。** 引文："a weak receipt treated as confirmation, an observation used as a write"。判定 CrowdStrike 2024 RCA 是否属于「weak receipt」是语义判断，不是语法检查。实际演练：CrowdStrike 的写对象是 channel file 部署，不是 ticket/disposition/approval——按准则 3 排除；但 R3 查询 `configuration deployment validator bug postmortem` 恰好就是为这类事件设计的，检索拉进来、过滤又排除，白耗额度。AWS S3 2017 同样死在准则 3（写对象是存储子系统状态）。**需要**：明确「准则 3 优先于准则 2」，即写对象清单是硬闸，避免执行者在「approval 绑定了不同变更」这类边界上自行发挥。

**7. §6 duplicate 的「primary URL」无定义。** NVD 条目和厂商 PSIRT 公告是同一事件，谁是 primary？v1 的 Q4 惯例是厂商公告，但本协议未写。**需要**：优先级序（PSIRT > NVD > GHSA）。

**8. §7 词汇禁令自相矛盾。** 引文："must not use SOC object-model vocabulary the constructor has not been shown… `close/bind/verify/egress` mediator names"。但我**被展示了** tei_threats.md，其中含有 `CLOSED`、outbox、eleven-segment fingerprint、`disposition_source_ref`，以及明文的 "The four SOC mediators (close / bind / verify / egress)"。§7 又说 "may use the published T1–T8 grid's language"——而网格的 SOC object 列全是实现词汇。§7 自己的示例 predicate（"the ticket reached closed"）也在用 `closed`。我到底能不能写 "reached CLOSED without a rebuilt outbox cycle"？**需要**：给出显式允许词表，或给 Constructor 一份删去 SOC object 列的网格副本，二选一。

**9. §7 引文「one sentence」无兜底。** 厂商公告常把关键事实拆在多句或表格里；付费论文（R4 允许 peer-reviewed paper，但 paywall 算不算 "public, citable"？）可能根本取不到可引句。**需要**：允许「≤2 句或 40 词」的放宽条款 + paywall 处理规则。

**10. §7 narrative 无完备性标准。** Implementer「不得越过冻结 narrative 去重查主源」（§3），但 §7 没规定 narrative 必须含足以建模的事实（时序、角色、字段）。写薄了，implementer 只能 `not_instantiable`；错在我还是在他？**需要**：narrative 必含要素清单。

**11. §8/§12 class guess 错了无人纠正、无处记录。** §8 只记录 harm predicate 与链的分歧；我的 `class_guess` 若与 implementer 实际映射不符，JSON 里没有 implementer 的 `mapped_class` 字段——schema 与 §8 职责不符。同理 §9 要求把「constructor's reasoning」交 arbiter，schema 无 `t9_reasoning` 字段。**需要**：schema 增补这两个字段。

**12. §12 三层冻结的机制不明。** 同一文件三个 freeze layer：Phase 1 冻结后 Phase 2 是原地改写还是追加？`class_guess` 在 arbiter 裁定 T9 后允不允许更新（§7 说 harm predicate "never edited"，class_guess 未说）？**需要**：写明「追加不改写」+ class_guess 的 T9 后处置规则。

**13. §9/§4 时序冲突。** T9 裁定要在「Phase 3 for that item」之前，但 §4 的 Phase 2 gate 是整体 arbiter review，表中无 T9 子 gate。**需要**：明确 T9 裁定嵌在 Phase 2 review 内还是独立门。

**不修就拒绝开工的 Top 3：**
1. **#8 词汇矛盾**——我是唯一被盲的角色，禁令不可判定等于整份 narrative 合规性不可判定。
2. **#1/#2/#3 检索可执行性**——R2/R4 无引擎、无串、无深度，「executed once」无定义，冻结查询形同虚设。
3. **#11/#12 schema 缺陷**——缺 implementer 映射字段和 t9_reasoning、冻结层机制不明，Phase 2/3 的产出无法落盘，T9 流程走不通。
