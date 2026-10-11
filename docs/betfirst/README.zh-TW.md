<p align="right"><a href="./README.md">English</a> · 繁體中文</p>

# BetFirst

**Make Cheap Bets. Win Big. Lose Small.**

**ALL IN？連關鍵假設都還沒測，就要全部押下去？**

Coding Agent 有時會查半天文件、翻原始碼、研究依賴、做出一整套 PoC，最後才發現：**一開始的假設根本不成立。**

**如果先做一個小測試，就能知道答案呢？**

BetFirst 讓 Agent 在值得的時候，先做一次安全、便宜、可停止的小實驗。測對了，省掉不必要的前期研究；測錯了，及早停手、回到正常解題。知道怎麼修的任務，就直接修，不必為了下注而下注。

<p align="center">
  <a href="../../media/betfirst/assets/betfirst-promo.mp4"><img src="../../media/betfirst/assets/betfirst-promo.gif" alt="BetFirst：先用一個小測試確認關鍵假設。" width="900"></a>
</p>

<p align="center"><a href="../../media/betfirst/assets/betfirst-promo.mp4">觀看完整影片 ↗</a></p>

## 立即開始

**直接請你的 Coding Agent 幫你安裝：**

```text
Install BetFirst for my coding agent. Follow https://github.com/tc3oliver/skills/blob/main/docs/betfirst/agent-install.md, detect my agent and existing installation, install only the BetFirst Skill, and verify it works.
```

**或使用 Agent Skills CLI**（依提示選擇 Agent 和安裝範圍）：

```bash
npx skills add tc3oliver/skills --skill betfirst
```

[Agent 安裝指引](./agent-install.md) · [查看 Skill 原始碼](../../betfirst/SKILL.md)

## BetFirst 怎麼做？

| NORMAL — 預設 | BET — 值得才做 | ABSTAIN — 已經正確 |
| --- | --- | --- |
| 知道怎麼修，就直接做。 | 一個小實驗能省掉大量調查？先試一次，設好停止條件。 | 需求本來就滿足？提出證據，不做無謂修改。 |

**不管有沒有下注，正式實作和最終驗證都不能省略。**


### 為什麼值得先賭一次？

原理其實很簡單：**預期省下的時間，要大於試錯可能付出的成本。**

$$
pS > (1-p)L + H
$$

\(p\) 是同類任務的*實測*成功率，\(S\) 是成功時省下的工作，\(L\) 是失敗後多付出的成本，\(H\) 是下注本身的開銷。沒有可靠數據就不要亂猜，更不用每次都下注。[看看背後的數學直覺 →](./WHY_BETFIRST.md)


### 例如：字幕路徑能不能用？

要知道字幕 Filter 是否接受某種特殊路徑，與其先把完整渲染流程組起來，不如拿一個假資料路徑做一次最小測試。能用，就繼續完成真正的修改；不能用，就保留錯誤訊息、正常調查。

**賭的是關鍵假設，不是整個解法的正確性。**

<p align="center">
  <img src="../../media/betfirst/assets/before-after.svg" alt="先做完整可行性研究，與先以最小實驗測試假設的概念比較。" width="900">
</p>

[更多例子](./examples.md) · [決策流程](../../media/betfirst/assets/decision-flow.svg)

## 真的有差嗎？

兩輪合計 **126 次本地 Muse Agent 執行**的合成任務研究中，BetFirst v0.4 相較測試過的對照策略有較低的耗時。第二輪的 **22 組雙方皆通過驗收的配對**裡，總耗時比 Efficiency 低 **17.9%**、比 No-BET 低 **18.0%**。

這是本地觀察，不代表每個模型、每個任務都能加速。舊版本曾在簡單任務變慢，Token 遙測也不完整。完整方法、失敗案例與限制都公開保留。

[查看完整實驗報告](../../research/betfirst/experiments/V04_RELEASE_RESULTS.md) · [實驗歷史](../../research/betfirst/experiments/EXPERIMENT_HISTORY.md)

## 不用換掉原本的工作流程

BetFirst 是只有指引文件的可攜式 Agent Skill，不需要額外 Runtime。Claude Code、Pi、OpenCode 等相容 Agent 都能使用；實際的探索與呼叫方式由各 Agent 決定。也可以獨立於 [Backlog](../../backlog/SKILL.md) 和 [Claude Team Kit](https://github.com/tc3oliver/claude-team-kit) 運作。

習慣 Claude Code Plugin？可執行 `/plugin marketplace add tc3oliver/skills`，再執行 `/plugin install tc3oliver-skills`；Plugin 與獨立 Skill 擇一安裝即可。

---

**Make Cheap Bets. Win Big. Lose Small.** · [開始安裝](#立即開始)

MIT 授權。
