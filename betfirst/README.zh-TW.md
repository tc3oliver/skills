<p align="center"><a href="./README.md">English</a> · <a href="./README.zh-TW.md">繁體中文</a></p>

<p align="center">
  <img src="./assets/hero.svg" alt="BetFirst — 小賭一把，贏大、輸小：先以低成本探測可行性，再決定是否投入大量研究。" width="1000">
</p>

# BetFirst

### Make Cheap Bets. Win Big. Lose Small.

**小賭一把，贏大、輸小。**

**Coding Agent 常常花很多時間，才搞清楚一個想法到底可不可行。** 先讀文件、查原始碼、研究依賴、比較方案、建立完整 PoC……但有時真正的關鍵，只需要先做一個很小的測試就能確認。

**如果先賭一把呢？**

BetFirst 讓 Agent 在投入大量前置研究之前，先尋找一個**成本極低、可以推翻假設、能安全回復**的可行性探測。這不是亂猜，而是用很小的成本，換取可能省下大量工作的機會。

| **賭贏：贏大** | **賭輸：輸小** | **不值得賭：別硬賭** |
| --- | --- | --- |
| 一個小實驗就確認關鍵可行性，省掉不再必要的研究或完整 PoC。 | 驗證失敗或結果不明，依預設上限立即止損，保留證據，回到正常調查。 | 找不到便宜、安全、結果明確的實驗，就照正常流程。原本沒問題就不修改。 |

**賭的是假設，不是程式正確性。** 後續實作、整合與正式驗收，一樣不能省略。

**Claude Code · Pi · 可攜式 Agent Skill · 實驗性 v0.2 · 不需要額外 Runtime**

## 30 秒，先下一個小賭注

用 Agent Skills CLI 安裝：

```bash
npx skills add tc3oliver/skills --skill betfirst -g -a claude-code -y
```

交給 Agent 一個真實任務：

```text
Use BetFirst. Before spending time on feasibility research or a full
PoC, see if one small, safe, reversible experiment can settle the key
uncertainty. Set a stop condition first. If it works, skip only the
preparation now made unnecessary. If it fails, stop and investigate
normally. Preserve existing work and complete final verification.
```

**偏好 Claude Code Plugin？** 執行 `/plugin marketplace add tc3oliver/skills`、`/plugin install tc3oliver-skills`，再呼叫 `/tc3oliver-skills:betfirst`。Plugin 與 CLI **擇一安裝**即可。

## 為什麼要先賭？

<p align="center">
  <img src="./assets/before-after.svg" alt="概念比較：一般流程可能先查文件、研究、做完整 PoC 才嘗試；BetFirst 先做一個低成本可行性探測，成功跳過不必要的前置工作，失敗停止並正常調查，最後都要正式驗收。" width="1000">
</p>

<sub>這是**概念示意**，不是實際 Benchmark 耗時比較。[動畫示意 →](./assets/probe-loop.gif)</sub>

**賭贏**不代表整個專案已經完成，而是某些前置研究不必再做。**賭輸**也不代表毫無收穫：便宜地推翻錯誤假設，本身就能避免走冤枉路。真正重要的是事先設好停止條件，而且真的停手。

### 例子：真的需要先做完整 PoC 嗎？

*示意情境，不是已驗證的 Benchmark 紀錄。*

```text
問題      字幕 Filter 到底能不能接受我們需要的路徑格式？
正常流程  查大量文件、研究跳脫規則、組出完整渲染 PoC，
          最後才真正嘗試。
小賭注    用一個假資料路徑和最小 Filter 呼叫直接測。
賭贏      確認可行，省下不必要的可行性研究，
          實作真正修正，然後正常驗收。
賭輸      立即停止，保留錯誤訊息作為證據，
          再回頭研究文件、程式碼或其他方案。
```

**小賭注本身也可能是一個極簡 PoC。** BetFirst 不是反對 PoC，而是反對還沒試過關鍵假設，就先為了完整 PoC 投入太多成本。

## BetFirst 如何決定下注？

**SPOT → CAP → BET → WIN / CUT LOSS**

**SPOT**：找到值得驗證、可能讓調查變昂貴的不確定性。**CAP**：先限制時間、影響範圍及回復成本。**BET**：用最小、安全、可推翻假設的實驗取得訊號。**WIN**：跳過證據已證明不再必要的前置工作。**CUT LOSS**：超出限制、失敗或結果不明就停止，保留證據，回到 **NORMAL**。

若涉及正式環境寫入、憑證、破壞他人修改或無法停止的實驗，就**不要賭**。需求已經滿足則 **ABSTAIN**，不做無謂修改。

[決策流程 →](./assets/decision-flow.svg) · [背後的方法論 →](./docs/WHY_BETFIRST.md)

## 放進現有的 Coding Agent 就能用

**Claude Code：** 依上方 CLI 或 Plugin 安裝，不需要另外啟動 Agent 或強制蒐集 Telemetry。

**Pi：** 將完整 `betfirst/` 放進 Pi 能探索的 Skill 目錄（例如 `~/.pi/agent/skills/betfirst/`），再執行 `/skill:betfirst`。[核心 Skill](./SKILL.md) 不依賴 Claude 專屬 Runtime。

**其他相容 Agent：** 可使用可攜式 `SKILL.md`；自動探索功能取決於工具。BetFirst 不依賴 Backlog 或 Claude Team Kit。

## 初步實驗：賭贏、賭輸都記錄

本地 Qwen/oMLX 探索性測試中，BetFirst 在**三道簡單題反而較慢**；在**兩道診斷題、各重複三次**時，相較 Efficiency-only 減少 **33.8% 耗時**與 **38.0% Gross Tokens**，雙方皆 **6/6 PASS**。這些只適用於該小型測試情境，**不是通用或因果加速證明**。

另外已預先固定的 **12 題、108 次 Evaluation v3**，**目前尚未公布結果**；正面與負面結果都會呈現。

[完整實驗歷史 →](./experiments/EXPERIMENT_HISTORY.md) · [v3 實驗規格 →](./experiments/V3_PROTOCOL.md)

## 分享 BetFirst

[**X 發文圖片與草稿 →**](./docs/X_MEDIA_KIT.md) · [決策範例](./references/examples.md) · [評估方法](./evals/README.md) · [核心 Skill](./SKILL.md) · [Changelog](./CHANGELOG.md)

**Make Cheap Bets. Win Big. Lose Small.** 把成本省在「搞清楚可不可行」，而不是犧牲「最終做得對不對」。

MIT 授權。
