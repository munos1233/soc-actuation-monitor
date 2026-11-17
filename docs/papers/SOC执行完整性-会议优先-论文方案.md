# 论文方案：属性准入对事务证据不完备（TOPS 在投）

> 目标刊是 **ACM TOPS**，书模 `acmart acmsmall,manuscript,review,anonymous`，硬限制总计 **35 页**（[ACM TOPS Author Guidelines](https://dl.acm.org/journal/tops/author-guidelines)）。TISSEC 托管页仍写 30 页，那是过期规则。投稿入口：`https://mc.manuscriptcentral.com/TOPS`。
>
> 实施与验收以 `paper/main.tex` 和 `paper/cover-letter.md` 为准。

---

## 0. 一页决策

- **目标刊：** ACM TOPS。
- **标题：** *Attribute Admission Is Incomplete for Transactional Evidence*。
- **一句话贡献：** Clark–Wilson 的 IVP 若填成请求视图函数 \(\pi\in\Pi\)（含 HMAC 与 attached copy），则 close/bind 不可判定（接口引理，不是新公理）；四条证据门 + 库角色把作者构造的边界注入从 naive 47/57 收到 full 0/57。kind / held-out 是映射，不是原产品复现。
- **不写的东西：** 新完整性公理、外部威胁语料、CVE 已在原产品复现、TLC 证明实现、保护域、第二家 LLM、live XDR、产品名。
- **形式化：** Java TLC 已跑 finite slice（full **10800** 状态，约 10× 旧切片）；不是实现对的证明。`minus CAS` 违反 `InvCAS`（不再与 full 同构空转）。`tei-reads-s.cfg` 是 AttributeOnly 的对偶（读 \(S\) 无 CE）。

---

## 1. 贡献（与正文 C1–C5 对齐）

- **C1** 接口引理：\(\Pi\) 不能实现 TEI-(ii)。16/45 与 kind 9/11 是 \(\Pi\) 的测量，不是引理的证明。
- **C2** SOC 构造：四门 + `actuation_writer`。
- **C3** 作者构造套件上的边界注入；LLM 臂是存在性检查。
- **C4** TLA+ 同一 `Next`；Java TLC finite slice 10800；卸一门有最短 CE；`minus CAS` 有 `InvCAS` CE。
- **C5** 作者控制的 kind：真 API 子集与 `tei.lab` 映射分表，*mapped, not reproduced*。fixture 22/22 只当 CI。

---

## 2. 评测口径

- 主表：naive **47/57**、full **0/57**；pseudo-live full **0/29**。57 = 作者边界注入。
- A3 naive **0/4** 是 substrate，不是四门。
- OPA / HMAC：**16/45**（A1–A5）；harness markdown 16/57 含 A0。
- Planner：只报 **glm-5.3**（N=5），存在性检查。
- K8s 真 API 列与 `tei.lab` 映射列分表；不与 57 混表。OPA 16 即 `needs_store_join`。
- 不要把 `artifacts/dynamic-eval-matrix/` 当论文证据。

---

## 3. 送审包

- `paper/main.pdf`（`make paper-pages` ≤ 35）
- 匿名 zip（`scripts/pack_paper_artifact.sh`；含 Makefile 或无 make 等价命令）
- `paper/cover-letter.md`（引理口径；默认两进程 + 42501）
- 投稿表勾选 ACM 生成式 AI
