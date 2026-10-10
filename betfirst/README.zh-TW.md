<p align="center"><a href="./README.md">English</a> · <a href="./README.zh-TW.md">繁體中文</a></p>

<p align="center">
  <img src="./assets/hero.svg" alt="BetFirst — 小賭一把，贏大、輸小" width="1000">
</p>

# BetFirst

> **如果 Coding Agent 能先花 10 秒驗證假設，為什麼要先花 10 分鐘調查？**

**Make Cheap Bets. Win Big. Lose Small.** 小賭一把，贏大、輸小。

BetFirst 是一個給 Coding Agent 使用的**成本感知執行策略（Cost-Aware Execution Skill）**：當一個**小型、可證偽、可回復**的實驗，有機會省下大量調查成本時，就先試；如果失敗，**立即止損**，保留線索，回到正常開發流程。

**以 Claude Code 為主 · 相容 Pi · 不增加執行階段依賴**

> [!IMPORTANT]
> **目前為實驗性 v0.1。** BetFirst 提供的是決策策略，**尚未證明可以節省多少時間、Token 或費用**。本文中的例子與數字均非 BetFirst 實測結果。請參考[評估方法](evals/README.md)。

## 30 秒開始使用

透過現有 Claude Code Plugin 安裝（步驟見下方），執行 `/tc3oliver-skills:betfirst`，然後交給 Agent 一個真實開發任務。

```text
Use BetFirst for this task. If a cheap, reversible probe can settle
a key uncertainty, take that bet. Stop immediately if it fails or
becomes inconclusive, preserve my existing work, and finish with
the normal correctness checks.
```

**下注不是強制流程。** 如果找不到低成本、結果明確、風險受控的實驗，就照正常方式開發。

## 為什麼需要 BetFirst？

Coding Agent 有時會先讀取大量檔案、追查依賴、分析可能原因，最後才做一個很小的驗證。某些問題確實需要完整調查；另一些問題，可能只要執行一條測試命令就能先排除重要的不確定性。

**BetFirst 只針對後者。** 用可控制的小損失，換取跳過高成本調查的機會。

| BetFirst **是** | BetFirst **不是** |
| --- | --- |
| 選擇何時值得做最小實驗的決策策略 | 亂猜後直接交付 |
| 用便宜的執行證據取代不必要的推測 | 略過必要測試的藉口 |
| 失敗有上限、可快速回到正常流程 | 系統化 Debug 的替代品 |
| 跨 Agent 可攜的指令 | 新的 Runtime、Daemon 或 Framework |

<p align="center">
  <img src="./assets/before-after.svg" alt="一般廣泛調查與 BetFirst 最小實驗流程的示意比較，非實測效能數據" width="1000">
</p>

## 運作原理：先找賭注，再限制損失

<p align="center">
  <img src="./assets/decision-flow.svg" alt="BetFirst 決策流程：尋找機會、限制風險、實驗、成功保留或失敗止損" width="1000">
</p>

**SPOT → CAP → BET → WIN / CUT LOSS**

1. **SPOT（找機會）**：找到具體、可證偽、能用最小實驗確認的假設。成功後必須能省下明顯更多的工作。
2. **CAP（限制損失）**：在執行前確定失敗訊號、停止條件和安全回復方式。優先使用只讀探測、臨時檔與現有聚焦測試。
3. **BET（下注）**：只讀取安全執行所需的上下文，改變一個變數，取得明確證據。
4. **WIN（贏）**：保留有證據支持的結果，跳過已不必要的調查，接著完成正常的驗收與回歸測試。
5. **CUT LOSS（止損）**：假設被否定、結果不明確、成本超標或行為變得不安全時，停止實驗；保留錯誤線索，只回復自己造成的變更，回到正常流程。

**NORMAL（正常調查）**：沒有合適賭注就使用原有開發流程。

**ABSTAIN（不動作）**：需求已經滿足時，不為了下注而修改程式碼。

### 哪些情況絕對不下注？

正式環境寫入、不可逆或破壞性操作、密鑰及敏感資料、無法確認回復邊界、會覆蓋使用者尚未提交的變更、沒有客觀驗證訊號，或成功也省不了多少工作的情況。

BetFirst 不會覆蓋 Agent 或專案原有的權限邊界，也不會降低 Definition of Done、Acceptance Criteria 或必要測試的要求。

## 安裝與使用

BetFirst 已整合於 [tc3oliver/skills](https://github.com/tc3oliver/skills) 現有 Skills 集合，**Claude Code 優先支援，Pi 使用同一份 `SKILL.md`**。Claude 只需選擇一種安裝方式，避免重複載入。

### Claude Code：Plugin 安裝

在 Claude Code 中執行：

```text
/plugin marketplace add tc3oliver/skills
/plugin install tc3oliver-skills
```

以 `/tc3oliver-skills:betfirst` 明確啟用，也可以在開發需求中指定使用 BetFirst。其 `description` 亦可供相容的 Agent 自動探索，但它**不會自動啟動額外 Agent 或背景服務**。

### Portable Agent Skills 安裝

```bash
npx skills add tc3oliver/skills --skill betfirst -g -a claude-code -y
```

### Pi

將完整的 `betfirst/` 目錄放入目前 Pi 版本可探索的 Skills 位置（例如 `~/.pi/agent/skills/betfirst/` 或 `~/.agents/skills/betfirst/`），並執行：

```text
/skill:betfirst
```

核心 Skill 不依賴 Claude 專屬工具，因此不需要維護第二套指令。實際載入方式請以安裝的 Pi 版本為準。

### 實際使用範例

```text
Use BetFirst while fixing the FFmpeg subtitle failure.
If a cheap reversible test can eliminate extensive investigation,
take it; if it fails, cut the loss and diagnose normally.
Preserve my existing changes and complete normal final validation.
```

BetFirst 專門決定「如何用較低成本取得下一個重要證據」。它可以與同一 Repository 的 `diagnosing-bugs` 搭配：用 BET 加速建立可重現的測試迴圈，而不是跳過根因分析或回歸測試。

## 為什麼這個方法可能有效？

Coding Agent 每一次推理、讀檔、輸出大量工具結果及反覆執行測試，都需要時間和 Token。額外分析的價值，取決於它能否帶來**比分析成本更大的決策改善**。

這和 **Rational Metareasoning（理性後設推理）**、**Cost-Aware Exploration（成本感知探索）** 的研究方向一致。2026 年的 Coding Agent 成本研究亦指出，現有 Agent 會出現可避免的效率浪費。這些研究提供設計動機，**不代表已驗證 BetFirst 的效能**。

對**單一成本指標**，例如時間或 Token，預期節省可以寫成：

```text
E[saved] = p * S - (1 - p) * L - H
break-even p > (L + H) / (S + L)
```

- `p`：從相似任務實際量測得到的成功機率，不能由模型憑空編造。
- `S`：賭贏後相較正常流程省下的成本。
- `L`：賭輸增加的成本，**包含清理與回到正常流程的額外成本**。
- `H`：採用 BetFirst 這套決策策略本身產生的額外開銷。

**純示意例子**：成功省下 9 分鐘、失敗多花 1 分鐘，且決策額外成本已包含在這兩個值內，打平所需成功率就是 **10%**。

時間和 Token 必須**分別**評估；跑得比較快，並不代表 Token 或金錢費用一定比較低。

在真實執行時，Agent 不需要為每次下注寫一份成本分析報告，也不應自行產生沒有校準的成功機率。先用便宜、明確的規則判斷；等累積真實數據，再研究動態成功率模型。

### 研究與參考資料

- Russell & Wefald，*Principles of Metareasoning*（1991）：https://doi.org/10.1016/0004-3702(91)90015-C
- *Calibrate-Then-Act: Cost-Aware Exploration in LLM Agents*（2026）：https://arxiv.org/abs/2602.16699
- *Analyzing and Mitigating Cost-Inefficient Behaviors in Coding Agents*（2026）：https://arxiv.org/abs/2609.30725
- Matt Pocock，*writing-for-agents*（精簡關鍵詞、上下文指標、移除無效指令）：https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents

BetFirst 的指令與決策策略由本 Repository 原創；上述資料是參考文獻，不是直接複製其他專案的 Skill。

## 賭贏、賭輸，以及不該賭的情況

| 情境 | 判斷 | 行為 |
| --- | --- | --- |
| FFmpeg 字幕路徑跳脫錯誤，可用小型 Fixture 驗證 | **可能 BET / WIN** | 先用最小命令驗證，確認後再做完整渲染測試 |
| TTS 重新採樣後異常沒有改善 | **CUT LOSS** | 停止該假設、保留證據，回到正常診斷 |
| 修改正式資料庫 Schema | **NORMAL** | 不對不可逆的正式狀態投機實驗 |
| 現有功能已符合驗收條件 | **ABSTAIN** | 不做無意義修改 |
| 實驗會覆蓋使用者尚未提交的程式碼 | **NORMAL / 只讀 BET** | 保護原有工作 |

詳細判斷訊號請見 [references/examples.md](references/examples.md)。

## 量測方式與 Benchmark

**Skill 本身不是 Telemetry Collector。** 一般 Coding 任務不應為了計量而增加大量日誌、Worktree、計畫或額外工具呼叫。

本專案提供[評估規範](evals/README.md)、[決策案例](evals/cases.json)以及[使用 Python 標準函式庫的 CSV 分析工具](scripts/analyze_runs.py)。

評估設計使用三組控制實驗：

1. **Baseline**：原始 Coding Agent，不載入 BetFirst。
2. **Efficiency**：僅要求避免冗餘讀檔、工具呼叫與重複測試。
3. **BetFirst**：相同效率規則加上 BetFirst 決策策略。

同一任務必須使用相同的初始 Commit、模型設定、驗收測試和隔離 Session。計入**失敗任務**、失敗下注、回復成本，以及 Skill 本身造成的額外 Token。成功與否必須由獨立的驗收標準判定，不能只相信 Agent 自述。

```bash
python3 -m unittest discover -s betfirst/tests
python3 betfirst/scripts/analyze_runs.py path/to/measured-runs.csv
```

分析器會比較配對任務的實際耗時、總 Token 與 API 金額。Telemetry 不完整時會顯示 `null`，不自行補值。它是**分析工具，不是自動執行 Benchmark 的 Harness**；尚未輸入真實數據前，沒有任何節省數字可宣稱。

## Roadmap

- **v0.1（目前）**：跨 Agent 的下注決策規則、止損邊界、案例與可重現的分析規範。
- **v0.2**：收集 Claude Code、Pi 的真實任務資料；分析錯誤下注、錯失賭注及停損成本，與 Baseline / Efficiency 比較。
- **v1.0**：公開可重現的跨任務評估；只有數據證明值得，才加入額外 Runtime Instrumentation 或強制控制機制。

## 分享與貢獻

**你遇過 Coding Agent 花很久調查、最後只靠一個小實驗就找到答案的案例嗎？** 歡迎提供可重現任務、起始 Repository 狀態、驗收測試，以及真實使用量。尤其歡迎回報「不該賭卻賭了」、「該賭卻錯過」與「該停卻沒停」的案例。

參考 [evals/README.md](evals/README.md) 了解如何進行公平對照。

> **我們要減少的是不確定性的成本，不是軟體品質。**

## 授權

MIT；依本 Repository 的授權條款。
