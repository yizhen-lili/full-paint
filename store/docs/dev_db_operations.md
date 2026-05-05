# Dev DB 操作記錄

> 開發過程中對 Railway production DB 做的手動操作（seed / patch / cleanup）一律記在這裡。
> 規則：[memory `feedback_no_fake_data.md`](../../C:/Users/yizhen/.claude/projects/d--website-PaintLearn/memory/feedback_no_fake_data.md) — 前端禁止寫死假資料；DB 沒資料時可手動 seed 真實資料，但必須記錄到本檔。

---

## 模板

每筆記錄包含：

```markdown
### YYYY-MM-DD HH:MM — <簡短描述>

**目的**：為什麼要做（哪個 stage / 哪個 page 需要這份資料）
**方式**：SQL / admin API / 後端 script
**影響的表**：themes / products / users / ...
**操作內容**：
\`\`\`sql
INSERT INTO themes (id, name, ...) VALUES (...);
\`\`\`
或
\`\`\`bash
curl -X POST http://localhost:8001/api/v1/admin/themes ...
\`\`\`
**回滾方式**：如何刪除這份資料（DELETE FROM ... WHERE id = ...）
```

---

## 操作記錄

（按日期由新到舊）

### 2026-05-05 — 初始檔案建立

尚無實際操作。S01 階段如果發現 Railway DB 主題 / 商品 / 客製案例為空、影響 mega-menu / 列表頁顯示「建設中」狀態，會在此補真實 seed 操作。
