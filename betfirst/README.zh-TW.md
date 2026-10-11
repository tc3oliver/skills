<p align="center"><a href="./README.md">English</a> · <a href="./README.zh-TW.md">繁體中文</a></p>

<p align="center">
  <img src="./assets/hero.svg" alt="BetFirst — 小賭一把，贏大、輸小。賭的是假設，不是程式正確性。" width="1000">
</p>

# BetFirst

### Make Cheap Bets. Win Big. Lose Small.

**小賭一把，贏大、輸小。**

**你的 Coding Agent 其實一直都在下注。** 猜測根因、決定先讀哪個檔案、嘗試某個修法，都是在賭「下一步值得花這個成本」。

**BetFirst 不是叫 Agent 不要賭，而是教它賭得更聰明。**

在花大量時間調查之前，先看看能不能用一個**小型、可證偽、可回復**的實驗，迅速確認或推翻關鍵假設。

| **賭贏：贏大** | **賭輸：輸小** | **不值得賭：收手** |
| :--- | :--- | :--- |
| 小探測就排除昂貴的錯誤方向。 | 假設錯了也有停損點，安全回到正常流程。 | 沒有好賭注就正常開發；程式本來沒錯就不要動。 |

**賭的是假設，絕不賭程式正確性。**

Claude Code · Pi · 可攜式 Agent Skill · 實驗性 v0.2 · 不需要額外 Runtime

## 30 秒，開始你的第一注

**使用 Agent Skills CLI 安裝：**

~~~bash
npx skills add tc3oliver/skills --skill betfirst -g -a claude-code -y
~~~

然後把任務交給 Agent：

~~~text
Use BetFirst. Before investigating broadly, look for one cheap,
falsifiable, reversible bet that could resolve the uncertainty.
Define what would disprove it and when to stop. If no good bet
exists, work normally. Preserve my changes and run final checks.
~~~

**偏好 Claude Code Plugin？** 依序執行 `/plugin marketplace add tc3oliver/skills`、`/plugin install tc3oliver-skills`，再呼叫 `/tc3oliver-skills:betfirst`。Plugin 與 CLI **擇一安裝**，避免重複載入。

## 真正厲害的，是知道怎麼輸

很多 Coding Agent 的流程只談測試成功。**BetFirst 也重視賭輸的時候。**

重點不是一開始猜得對不對，而是能不能在調查變昂貴之前，花一點成本取得有價值的證據。

<p align="center">
  <img src="./assets/probe-loop.gif" width="760" alt="概念動畫：比較廣泛探索與 BetFirst 小型探測、取得證據、完成驗證的流程；並非真實模型紀錄或實驗數據。">
</p>

<sub>此動畫為流程示意，**不是**真實 Agent 執行錄影或量測到的加速效果。[靜態比較圖 →](./assets/before-after.svg)</sub>

### 一個賭注，兩種結果

*以下為示意情境，不是真實 Benchmark Trace。*

~~~text
BUG       Windows 磁碟路徑導致字幕渲染失敗。
假設      磁碟代號後的冒號沒有正確跳脫。
下注      用一個代表性路徑跑最小、隔離的 Filter 測試。

賭贏      驗證假設成立 → 修正跳脫邏輯，完成必要的
          Renderer 與回歸測試。

賭輸      假設被推翻 → 停止追這個方向，保留證據，
          改查下一個可能原因。
~~~

**賭輸，不代表任務失敗。** 用很低的成本推翻錯誤理論，可能比直接寫出錯誤修正更有價值。同樣地，賭贏也不代表可以跳過驗收。

## 會下注，也要會收手

**SPOT → CAP → BET → WIN / CUT LOSS**

| 決策 | Agent 應該做的事 |
| --- | --- |
| **SPOT／找賭注** | 找到明確、可以被推翻的假設，而不是憑感覺亂猜。 |
| **CAP／設停損** | 執行前訂好成本上限、成功與失敗訊號、回復方式。 |
| **BET／下注** | 用最小、可逆的測試取得真正有用的證據。 |
| **WIN／賭贏** | 根據證據縮短不必要的探索，然後完成正常驗收。 |
| **CUT LOSS／認賠收手** | 假設錯誤或結果不明時停止探測，保留線索，回到正常 Debug。 |
| **NORMAL／ABSTAIN** | 沒有值得的賭注就正常開發；問題原本已解決就不修改。 |

**不能拿來賭的事：** 正式環境寫入、破壞性 Git 清理、憑證、無法限制成本的實驗，以及省略必要測試。BetFirst 是一套決策策略，不是讓 Agent 冒險修改資料或交付未驗證程式碼的藉口。

[完整決策流程 →](./assets/decision-flow.svg) · [背後的判斷方法 →](./docs/WHY_BETFIRST.md)

## 一個小 Skill，不必換整套工具

**Claude Code：** 使用上方 Skills CLI 或 Plugin 安裝，可以手動呼叫，也能由相容的 Skill 探索機制選用。

**Pi：** 將完整 `betfirst/` 目錄放進目前 Pi 能探索的 Skills 路徑（例如 `~/.pi/agent/skills/betfirst/`），呼叫 `/skill:betfirst`。核心 [`SKILL.md`](./SKILL.md) 不依賴 Claude 專屬 Runtime。

**其他相容 Coding Agent：** 可以讀取這份可攜式 Skill，是否支援自動探索依工具而異。BetFirst 可單獨使用，不需要 Backlog、Claude Team Kit 或新任務框架。

## 下注真的有賺嗎？

**有時有，有時沒有。這正是 BetFirst 要解決的問題。** 初步本地 Qwen/oMLX 實驗中，BetFirst 在**三道簡單題反而較慢**；但在**兩道診斷題、各重複三次**時，相較 Efficiency-only 節省 **33.8% 耗時**、**38.0% Gross Tokens**，雙方皆 **6/6 PASS**。

這些只是**探索性觀察**，不代表所有任務都能加速，也不能當成因果證明。更完整的 **12 題、108 次 Evaluation v3** 已有預先固定的實驗規格，**結果待公布**；賭贏與賭輸都會揭露。

[完整實驗歷史 →](./experiments/EXPERIMENT_HISTORY.md) · [v3 實驗規格 →](./experiments/V3_PROTOCOL.md)

## 讓 Agent 成為更好的下注者

安裝 BetFirst，給它一個真實的 Debug 任務，看看是否值得先用一個小賭注買到決定性證據。**有證據就贏大；證據不足就輸小、收手。**

[決策案例](./references/examples.md) · [評估規範](./evals/README.md) · [核心 Skill](./SKILL.md) · [Changelog](./CHANGELOG.md)

**Make Cheap Bets. Win Big. Lose Small.**

MIT 授權。
