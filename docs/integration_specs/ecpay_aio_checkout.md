# ECpay 全方位金流 AioCheckOut — 技術規格

> Module 23 金流整合的 ECpay API 規格對照。對應 [module_plans/23_payment_ecpay.md](../module_plans/23_payment_ecpay.md)。
> 官方文件：ECpay 全方位金流 / 信用卡 / ATM / 超商代碼。**金流簽章用 SHA256**（物流用 MD5）。

---

## 1. Endpoints

| 用途 | Stage | Production | Method |
|---|---|---|---|
| 結帳（AioCheckOut） | `https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5` | `https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5` | 瀏覽器 POST（auto-submit form） |

> 結帳是「瀏覽器把 hidden form POST 到 ECpay 結帳頁」，非後端 httpx 呼叫（與物流 Express/Create 不同）。
> ReturnURL / PaymentInfoURL 是 **ECpay server-to-server POST 回我們**。

---

## 2. AioCheckOut 送出參數（我們組，含 CheckMacValue）

| 參數 | 必填 | 值 / 來源 | 備註 |
|---|---|---|---|
| MerchantID | ✓ | `settings.ecpay_payment_merchant_id` | 金流帳號 |
| MerchantTradeNo | ✓ | `PAY` + yyMMddHHmmss + 4 hex（≤20 字、英數） | 唯一；存入 `payment_transactions.merchant_trade_no` |
| MerchantTradeDate | ✓ | `yyyy/MM/dd HH:mm:ss` | 建立交易時間 |
| PaymentType | ✓ | `aio` | 固定 |
| TotalAmount | ✓ | `int(order.total)` | **整數**，ECpay 不收小數 |
| TradeDesc | ✓ | 例：`易木 YIIMUI 訂單 {order_number}` | |
| ItemName | ✓ | 商品名稱，多項用 `#` 分隔，≤400 字 | **分隔符是 `#` 不是 `,`** |
| ReturnURL | ✓ | `{base}/api/v1/payment/ecpay/return` | server-to-server 付款結果（權威） |
| ChoosePayment | ✓ | 階段1 `Credit`；階段2 `ALL` | Credit/WebATM/ATM/CVS/BARCODE/ApplePay/ALL |
| EncryptType | ✓ | `1` | 1 = SHA256 |
| OrderResultURL | — | `{base}/api/v1/payment/ecpay/result` | 顧客瀏覽器 POST 導回；**不可標 paid** |
| ClientBackURL | — | 前端結果頁 URL | 顧客按「返回商店」 |
| PaymentInfoURL | — | `{base}/api/v1/payment/ecpay/payment-info` | ATM/超商**取號**通知（階段2） |
| ClientRedirectURL | — | 前端「等待繳費」頁 | ATM/CVS 取號後顧客瀏覽器導向 |
| NeedExtraPaidInfo | — | `Y` | 回傳含手續費等額外資訊 |
| ExpireDate | — | ATM 繳費天數 1–60（待確認 §) | ATM 專用 |
| StoreExpireDate | — | CVS 繳費分鐘數 | CVS 專用 |
| CheckMacValue | ✓ | 見 §5 | 最後計算 |

---

## 3. ReturnURL 回傳參數（付款成功，server-to-server）

ECpay POST（`application/x-www-form-urlencoded`）主要欄位：

| 欄位 | 說明 | 我們用途 |
|---|---|---|
| MerchantID | 商店代號 | 可比對 |
| MerchantTradeNo | 我方單號 | **lookup payment_transactions 主鍵** |
| RtnCode | `1` = 付款成功；其他 = 失敗 | **判定付款成功唯一依據** |
| RtnMsg | 訊息 | 存 last_rtn_msg |
| TradeNo | ECpay 交易號 | 存 ecpay_trade_no |
| TradeAmt | 交易金額（整數） | **與 transaction.amount 比對防竄改** |
| PaymentDate | 付款時間 | |
| PaymentType | 實際付款方式（如 Credit_CreditCard / ATM_TAISHIN / CVS_CVS） | 存 payment_type |
| SimulatePaid | `1` = 後台模擬付款（非真實扣款） | 測試辨識 |
| CheckMacValue | 簽章 | **必驗** |

**我們必回**：`1|OK`（純字串 `PlainTextResponse`，不含 HTML/JSON）。未回或非 `1|OK` → ECpay 重送。
**驗章失敗 / 找不到單 / 金額不符**：回 `0|<reason>`（讓 ECpay 重送 + 不洩漏細節 + 絕不標 paid）。

---

## 4. PaymentInfoURL 回傳參數（ATM/超商取號，server-to-server）

「取號成功」通知，**RtnCode ≠ 1**，代表拿到帳號/代碼但**尚未付款**：

| 付款方式 | 取號成功 RtnCode | 額外欄位 |
|---|---|---|
| ATM 虛擬帳號 | `2`（待確認 §） | `BankCode`、`vAccount`、`ExpireDate` |
| 超商代碼 CVS | 依官方文件（待確認 §） | `PaymentNo`、`ExpireDate` |
| 超商條碼 BARCODE | 依官方文件（待確認 §） | `Barcode1`、`Barcode2`、`Barcode3`、`ExpireDate` |

處理：存帳號/代碼 + expire_date、transaction.status=`awaiting_atm`、order 維持 pending_payment、對齊 payment_deadline、寄 email。**必回 `1|OK`**。
顧客實際繳費後，ECpay 會再打 **ReturnURL（RtnCode=1）**，那時才標 paid。

---

## 5. CheckMacValue（SHA256）

與物流（`logistics/service.py`）演算法步驟相同，**只把 MD5 換成 SHA256**，金鑰用金流帳號：
1. 參數依 key 字典序升冪排序（排除 CheckMacValue 本身）
2. 串成 `HashKey={ecpay_payment_hash_key}&Key1=Val1&...&HashIV={ecpay_payment_hash_iv}`
3. `_ecpay_url_encode`（.NET style：`quote_plus(safe="-_.!*()")` 後轉小寫）
4. `hashlib.sha256(...).hexdigest()`
5. 轉大寫

`_ecpay_url_encode` 純函數可直接 from `logistics.service` import 復用。

驗章：取回傳參數（去掉 CheckMacValue）重算，與回傳值（轉大寫）比對相等。

---

## 6. 常用 RtnCode / 安全要點

- **付款成功**：ReturnURL `RtnCode == 1`（`is_payment_success`）。
- **取號成功（非付款）**：PaymentInfoURL ATM=`2` 等（`ATM_CODE_ISSUED_RTN_CODES` / `CVS_CODE_ISSUED_RTN_CODES`，確切值實作時查官方文件）。
- **唯一標 paid 路徑** = ReturnURL + 驗章通過 + RtnCode==1 + `int(TradeAmt)==int(transaction.amount)` + transaction 存在。
- OrderResultURL（瀏覽器）僅 redirect，**絕不標 paid**。
- 金額比對用 `transaction.amount`（發起時 order.total 快照），非當下 order.total，避免改價誤判。
- 可加驗 `MerchantID == settings.ecpay_payment_merchant_id`。

---

## 7. 待確認（同 module plan §8）

1. 金流 sandbox 測試帳號（暫用 3002607 / pwFHCqoQZGmho4w6 / EkRm7iFT261dpevs，需確認）
2. ATM ExpireDate / CVS StoreExpireDate 天數/分鐘數
3. ATM=2、CVS/BARCODE 取號 RtnCode 確切值（查官方文件）
4. 超商代碼/條碼上限 NT$20,000 的處理
