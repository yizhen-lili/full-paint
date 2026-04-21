# Module 5b：上傳模組（Upload）

> 此模組為製作系統（04_production.md）的附屬模組，不獨立存在。
> 所有上傳 endpoints 的業務邏輯均在 production/service.py 實作。
> 測試覆蓋於 tests/production/test_production.py。

## Endpoints

| Endpoint | 說明 |
|----------|------|
| POST /upload/production-image | 產生 Firebase Signed Upload URL（admin 限定） |

詳細規格見 04_production.md 及 docs/api.md 模組十九。
