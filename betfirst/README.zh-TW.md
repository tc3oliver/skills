<p align="center"><a href="./README.md">English</a> · <a href="./README.zh-TW.md">繁體中文</a></p>

<p align="center">
  <img src="./assets/hero.svg" alt="BetFirst：先做小型驗證，少走昂貴的錯路；利用可逆探測找到經驗證的解法。" width="1000">
</p>

# BetFirst

### 別讓 Coding Agent 一直猜。先驗證最重要的那件事。

**BetFirst** 是給 Coding Agent 的輕量級、成本感知決策 Skill。遇到需要大量調查的問題時，先判斷能不能用一個**小型、可證偽、可回復**的探測排除不確定性；不划算，就照正常方式處理。探測失敗，**立即止損**。

不需要新 Daemon、不必啟動額外 Agent、不強制蒐集 Telemetry，**也不會省略必要驗收**。

**Claude Code 與 Pi** · 可攜式 `SKILL.md` · 實驗性 v0.2

## 30 秒開始使用

**Claude Code — Portable Skill**

```bash
npx skills add tc3oliver/skills --skill betfirst -g -a claude-code -y
```

然後交給 Agent：

```text
Use BetFirst to fix this issue. If one cheap, reversible probe could
resolve the uncertainty, try it first. If not, work normally.
Preserve my changes and run the required final checks.
```

偏好 Claude Code Plugin？依序執行 `/plugin marketplace add tc3oliver/skills`、`/plugin install tc3oliver-skills`，再使用 `/tc3oliver-skills:betfirst`。**Plugin 與 Skills CLI 擇一安裝**，避免重複載入。

## BetFirst 改變了什麼？

<p align="center">
  <img src="./assets/probe-loop.gif" width="760" alt="概念動畫：一般探索可能經過許多步驟，BetFirst 嘗試可控制的小型探測，取得證據，再完成驗證；非實際錄影或 Benchmark。">
</p>

<sub>這是**流程概念動畫**，不是實際 Agent 紀錄或測量到的加速效果。[查看靜態比較圖](./assets/before-after.svg)。</sub>

在開始讀取十幾個檔案之前，先問：

> **有沒有一個便宜的小實驗，能快速排除昂貴的錯誤方向？**

| 情境 | BetFirst 的選擇 |
| --- | --- |
| 小型、安全的驗證能區分幾個可能原因 | **BET**：先試，並設定停止條件 |
| 測試風險高、結果模糊，或比直接處理更貴 | **NORMAL**：照原本流程開發 |
| 功能本來就符合需求 | **ABSTAIN**：不做無意義修改 |
| 探測失敗、超出成本或沒有決定性結果 | **CUT LOSS**：保留證據、停止下注、正常診斷 |

### 例子：字幕路徑出錯

*以下是示意案例，不是已驗證的 Benchmark 執行紀錄。*

```text
問題      Windows 磁碟路徑讓字幕渲染失敗。
假設      磁碟代號後的冒號沒有正確跳脫。
探測      用一個最小路徑案例執行 FFmpeg filter。
觀察      成功重現，確認冒號跳脫問題。
修正      只修改路徑轉換，然後完成正式測試。
```

好處是少做不必要的調查；但**不該下注時也要知道停手**。正式環境寫入、憑證、破壞性操作、無法控制的實驗，都不適合 BET。

## 怎麼運作？

**SPOT → CAP → BET → WIN / CUT LOSS**

**SPOT**：找出具體的不確定性；**CAP**：限制時間、影響與回復成本；**BET**：用最小、可證偽的方法取得訊號；**WIN**：確認證據後修復並完成測試。若沒有足夠證據，就 **CUT LOSS**，回到正常開發。

BET 不是跳過根因分析，更不能降低 Definition of Done 或 Acceptance Criteria。

[完整決策流程 →](./assets/decision-flow.svg) · [背後的方法論 →](./docs/WHY_BETFIRST.md)

## 放進你現有的 Agent 工作流

**Claude Code：** 使用上方 Plugin 或 Skills CLI 安裝，手動呼叫或讓相容的 Skill 探索機制選用。

**Pi：** 將完整 `betfirst/` 放進 Pi 能探索的 Skills 目錄（例如 `~/.pi/agent/skills/betfirst/`），再執行 `/skill:betfirst`。核心 `SKILL.md` 不需要 Claude 專屬 Runtime。

**其他相容 Agent：** 可以讀取可攜式 `SKILL.md`；是否自動探索取決於該工具。BetFirst 能單獨使用，不需要 Backlog 或 Claude Team Kit。

## 初步證據：好的、壞的都公開

本地 Qwen/oMLX 初步測試顯示，BetFirst 在**三個簡單任務反而較慢**；而在**兩個診斷任務、各重複三次**時，相較 Efficiency-only 減少 **33.8% 耗時**與 **38.0% Gross Tokens**，雙方皆 6/6 PASS。這只是**探索性觀察，不代表普遍加速，也無法證明因果關係**。

規模更大的 **12 題、108 次執行 Evaluation v3** 是本次公開發布前固定的最後一輪實驗；**目前結果待公布**，正面或負面都會完整揭露。

[完整實驗紀錄 →](./experiments/EXPERIMENT_HISTORY.md) · [v3 實驗規格 →](./experiments/V3_PROTOCOL.md)

## 延伸閱讀

[實際決策案例](./references/examples.md) · [評估方法](./evals/README.md) · [核心 Skill](./SKILL.md) · [Changelog](./CHANGELOG.md)

如果你有 Coding Agent 過度探索、或明明不該下注卻下注的可重現案例，歡迎提交 Issue。**我們要減少的是不確定性的成本，不是程式品質。**

MIT 授權。
