# Store Frontend 開發 SOP

> 完整 SOP 在 [admin/docs/frontend_sop.md](../../admin/docs/frontend_sop.md)，store 沿用同一套精神（規劃 → 對照規格 → 收問題 → 確認無衝突 → 才寫 code，每模組循環）。
>
> 本檔僅記錄 **store 專屬的差異點 / 補充規則**。

---

## Store 專屬補充

### 1. 模組命名前綴用 `S` 不用 `F`

- admin 的模組：`F01_app_shell_auth.md` ⋯ `F12_*.md`
- store 的模組：`S01_*.md` ⋯ `S10_*.md`（10 個，見 [module_plans/00_overview.md](module_plans/00_overview.md)）

避免兩邊規劃書檔名混淆。

### 2. 設計系統來源

每個模組規劃書「設計決策」段落必須引用 [design_system.md](design_system.md)，不重新發明色票、字體、間距。

如有局部例外（極少見），在規劃書「設計決策」段落明確記錄理由 + 影響範圍。

### 3. Commit 格式

```
feat(store/<module>): 完成 SXX - <模組名稱>
```

例如：`feat(store/auth): 完成 S04 - 會員認證`

### 4. 共用 admin 的開發 stack

- Vite + Vue 3 + TS + Tailwind 4
- Pinia + TanStack Query + openapi-fetch + VeeValidate + Zod
- httpOnly cookie JWT
- 路由 guard、API fetcher pattern 沿用 admin

差異：
- store 沒 sidebar nav，用 sticky top header + mega-menu
- store 攝影為主，圖片走 Firebase signed URL 直傳
- store 客戶端 SSE 接收（admin 端是 SSE 推播者）

### 5. 手動驗收必跑 chrome-devtools

每個 page 完成後用 chrome-devtools MCP：
1. `navigate_page` 到該頁
2. `take_screenshot` 全頁 + 重點區
3. `list_console_messages` 確認無 error
4. `list_network_requests` 確認 API 200 / 無 401 unexpected
5. `lighthouse_audit` 重要頁面 ≥ 90

### 6. 部署 Vercel

- repo 有兩個 remote，**Vercel 連的是 `yizhen-lili` 不是 `origin`**（見 memory `project_git_remotes.md`）
- push 前先 `git remote -v` 確認

---

### 7. 後端規格永遠從原始碼查，不憑印象

寫規劃書 / 規格比對 / API 串接時，**禁止憑記憶寫後端規格**。涉及任何後端的事（API endpoint、request/response schema、業務規則、欄位限制、狀態流轉、Event 副作用）必須去 backend 原始碼查證：

| 要查什麼 | 去哪查 |
|---|---|
| API endpoint 規格 | [docs/api.md](../../docs/api.md) → 對應 backend 模組 router.py / schemas.py |
| 資料表欄位 | [docs/schema.md](../../docs/schema.md) → backend models.py |
| 業務規則 | [docs/requirements/*.md](../../docs/requirements/) → backend service.py |
| Event 副作用 | [docs/EVENT_MATRIX.md](../../docs/EVENT_MATRIX.md) |
| 模組已實作 | [docs/module_plans/*.md](../../docs/module_plans/) + backend/<module>/*.py |

**原則**：規劃書中每個 API 對應、每條業務規則、每個欄位限制，都要附上來源（`docs/api.md:行號` 或 `backend/auth/router.py:行號`）。

**對應 memory rules**：
- [No Guessing](../../../C:/Users/yizhen/.claude/projects/d--website-PaintLearn/memory/feedback_no_guessing.md) — 不知道就查、查不清楚就問
- [Spec as System](../../../C:/Users/yizhen/.claude/projects/d--website-PaintLearn/memory/feedback_spec_as_system.md) — 改動單位是「概念」，每個概念跨多層
- [Question Discipline](../../../C:/Users/yizhen/.claude/projects/d--website-PaintLearn/memory/feedback_question_discipline.md) — 問題是最後手段：必須先讀完所有規格

---

## 其他規則一律參照 admin SOP

- 模組開始前必須寫規劃書（含路由 / API / 元件樹 / 狀態 / 表單 / 設計決策 / 手動驗收 / 待確認）
- 規劃書完成後必須產出規格比對報告（api.md / requirements/*.md / store_routes.md），有 ⚠️ 必須先解決
- 分段節奏：每個 page 一個循環
- 完成定義：TypeScript 0 錯 + Build 通過 + 手動驗收 + Console 乾淨 + Network 正常 + 風格一致 + a11y ≥ 90 + reviewer pass
- 模組完成後自動 git commit + 回頭驗收報告
