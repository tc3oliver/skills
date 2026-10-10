# Backlog v2

**記住工作、只讀需要的資訊、以證據完成。**

這是給 Coding Agent 使用的持久化任務 Skill。沒有 Backlog.md 套件、資料庫、Hooks、MCP、Installer 或背景服務。執行 CLI 只需要 Python 3.11 以上標準函式庫。

只有在需要記錄未來工作、跨 Session 恢復、追蹤優先級或任務依賴時才使用。一般 Coding、Debug、Review 不需要自動建立 Backlog。

## 安裝

```bash
npx skills add tc3oliver/skills --skill backlog
```

或用本 Repository 的 Claude Code Plugin。Pi 可以安裝完整 `backlog/` 目錄並載入同一份 `SKILL.md`。

## 使用

```text
/backlog add "新增 SSO 登入"
/backlog next
/backlog do BL-7E18C75F3D31A0B2
/backlog status
```

實際 Skill 呼叫語法依 Agent 而定。第一次使用明確初始化 `.backlog/`。也可以直接使用 CLI：

```bash
python3 <skill-dir>/scripts/backlog.py --root . init
python3 <skill-dir>/scripts/backlog.py --root . add "登入" --goal "支援 SSO" --ac "登入成功"
python3 <skill-dir>/scripts/backlog.py --root . next --limit 5
python3 <skill-dir>/scripts/backlog.py --root . doctor
```

`.backlog/tasks` 中每個 Task 一個 Markdown。`next` 只傳回少量 Metadata；`show ID` 才讀取完整任務。完成或取消後，移至 `.backlog/archive/YYYY-MM/`，保留歷史及依賴資訊。

狀態為 `inbox → todo → doing → done`，另有 `blocked` 和 `cancelled`。需求不完整可先放入 `inbox`，不強迫 Agent 編造驗收條件。只有依賴皆完成的 `todo` 會進入 Ready Queue。完成前需實際驗證 AC，保存驗證證據。

跨 Session 使用簡短 Handoff（已做、剩餘、關聯檔案、最近驗證、下一步），而不是整段對話記錄。恢復後必須重新確認目前程式狀態。

## 與既有 Skills 分工

- **BetFirst**：成本感知、可回復的小型實驗；不管任務生命週期，也不取代驗證。
- **CTK**：Agent Teams、並行、Review 與 Debug；只有 Lead 寫入持久 Backlog 任務，CTK Worker Task 不同步為 Backlog Task。
- **Backlog**：持久任務、優先級、依賴、恢復與完成證據；不自動啟動 BetFirst 或 CTK。

## 舊版

`backlog-workflow` v1.6 使用外部 Backlog.md 引擎與多階段流程。v2 是不相容重寫，不自動遷移或刪除舊專案中的 `.agent-workflow`、Backlog.md 任務。舊版程式碼保留在 Git 歷史與 `archive/backlog-workflow-v1.6.0` Branch。

詳見 [CLI 規格](references/cli.md)。
