---
title: 網站客服單

---

# 網站客服單

## 反向通訊：Bot 對 WordPress 的 API 呼叫規格

完整的系統是雙向的。當事件在 Discord 端發生時，Bot 也需要通知 WordPress。可以使用的 WordPress REST API 端點：

| 觸發情境 | Bot 執行目的 | Method | Endpoint | 參數 |
| :--- | :--- | :--- | :--- | :--- |
| 客服在 Discord 回覆 | 同步回覆到 WP | `POST` | `/wp-json/dragonshop/v1/ticket/update` | JSON Body: `{ "ticket_id", "sender", "message" }` |
| 客服在 Discord 關閉工單 | 同步狀態到 WP | `POST` | `/wp-json/dragonshop/v1/ticket/close` | JSON Body: `{ "ticket_id" }` |
| 建立頻道時顯示訂單資訊 | 從 WP 獲取訂單詳情 | `GET` | `/wp-json/dragonshop/v1/order/details` | Query Param: `?ticket_id=` |
| Bot 重啟後恢復頻道 | 從 WP 獲取工單歷史 | `GET` | `/wp-json/dragonshop/v1/ticket/get` | Query Param: `?ticket_id=` |
| Bot 重啟後恢復頻道 | 從 WP 獲取原始頻道名 | `GET` | `/wp-json/dragonshop/v1/ticket/channel_name`| Query Param: `?ticket_id=` |


## **1. 核心架構：事件驅動與 Webhook**

在深入細節之前，最重要是理解我們採用的核心架構模式：**以 WordPress 為事件來源的 Webhook 推送機制**。

  * **角色定義**：

      * **WordPress (發布者 Publisher)**：作為系統的「單一事實來源 (Single Source of Truth)」。所有客服單的建立、更新、關閉等核心事件，都源自於此。
      * **Discord Bot (訂閱者 Subscriber)**：作為一個事件的「監聽者 (Listener)」。它的主要職責是接收來自 WP 的通知，並將這些事件轉化為 Discord 上的具體操作。

  * **運作模式 (Push, not Pull)**：
    我們的通訊是**單向推送**的。當 WP 端有事件發生時，它會主動發送一個 HTTP POST 請求 (即 Webhook) 到 Bot 監聽的端點。這比讓 Bot 不斷輪詢 (Polling) WP 的 API 詢問「有新消息嗎？」要高效且即時得多。

  * **簡易流程圖**：
    `[WP 端事件觸發]` -\> `[PHP 程式打包 Payload]` -\> `[發送 HTTP POST Webhook]` -\> `[Bot 的 aiohttp 伺服器接收]` -\> `[Python 程式解析 Payload]` -\> `[執行對應的 Discord 操作]`

-----

## **2. Webhook API 規格**

這是最需要關注的部分。所有由 WP 發送的請求都遵循以下規則：

  * **請求方法**： `POST`
  * **內容類型**： `Content-Type: application/json`
  * **基礎 URL**： Bot 所監聽的根路徑 (e.g., `http://your-bot-ip:8000`)

### Endpoint 1: 建立新客服單

  * **Endpoint**： `POST /ticket/create`
  * **說明**： 當使用者在網站上成功建立一筆新的客服單時，WP 會立即呼叫此端點。
  * **Payload 欄位**：

| 欄位 (Field) | 類型 (Type) | 是否必須 (Required) | 說明 |
| :--- | :--- | :--- | :--- |
| `ticket_id` | Integer | 是 | WordPress 資料庫中的客服單唯一 ID。所有後續操作都將以此 ID 為依據。 |
| `ticket_title` | String | 是 | 使用者填寫的客服單主旨。 |
| `ticket_message` | String | 是 | 使用者的第一則訊息完整內容。 |
| `channel_name` | String | 是 | WordPress 建議的 Discord 頻道名稱。Bot 應使用此名稱建立頻道。 |
| `sender` | String | 是 | 發送者的身分資訊，格式通常為 `"[顧客] 姓名 (email@example.com)"`。 |
| `image_url` | String | 否 | 如果使用者有上傳圖片，此為 Imgur 的公開圖片連結。若無則此欄位不存在。 |

  * **範例 Payload**：
    ```json
    {
      "ticket_id": 33,
      "ticket_title": "關於訂單 #8806 商品運送問題",
      "ticket_message": "你好，我想請問我的訂單何時會出貨？謝謝。",
      "channel_name": "#網站-客-0033",
      "sender": "[顧客 - 初始訊息] DemoUser (demo@example.com)",
      "image_url": "https://i.imgur.com/aBcDeFg.png"
    }
    ```

### Endpoint 2: 更新客服單對話 (使用者新回覆)

  * **Endpoint**： `POST /ticket/update`
  * **說明**： 當使用者在網站上對一個已存在的客服單進行回覆時，呼叫此端點。
  * **Payload 欄位**：

| 欄位 (Field) | 類型 (Type) | 是否必須 (Required) | 說明 |
| :--- | :--- | :--- | :--- |
| `ticket_id` | Integer | 是 | 對應的客服單 ID。 |
| `sender` | String | 是 | 發送者的身分資訊。 |
| `message` | String | 是 | 使用者回覆的完整訊息內容。 |
| `channel_name` | String | 是 | 對應的 Discord 頻道名稱，主要用於恢復(restore)邏輯。 |
| `image_url` | String | 否 | 如果回覆時有附圖，此為 Imgur 圖片連結。 |

  * **範例 Payload**：
    ```json
    {
      "ticket_id": 33,
      "sender": "[顧客] DemoUser (demo@example.com)",
      "message": "好的，我了解了，感謝你的回覆。",
      "channel_name": "#網站-客-0033",
      "image_url": null
    }
    ```

### Endpoint 3: 關閉客服單

  * **Endpoint**： `POST /ticket/close`
  * **說明**： 當客服單在 WP 端被關閉時（由使用者、管理員或系統自動），呼叫此端點。
  * **Payload 欄位**：

| 欄位 (Field) | 類型 (Type) | 是否必須 (Required) | 說明 |
| :--- | :--- | :--- | :--- |
| `ticket_id` | Integer | 是 | 要關閉的客服單 ID。 |
| `channel_name` | String | 是 | 對應的 Discord 頻道名稱。 |
| `force_close` | Boolean | 是 | 通常為 `true`。 |
| `closed_by` | String | 是 | 記錄是由哪一方關閉的。可能的值為：`"網站/客戶端"`、`"網站/管理端"`、`"系統自動關閉"`。 |

  * **範例 Payload**：
    ```json
    {
      "ticket_id": 33,
      "channel_name": "#網站-客-0033",
      "force_close": true,
      "closed_by": "網站/客戶端"
    }
    ```

-----

## **4. 除錯與常見問題 (FAQ)**

1.  **問題：我確定 WP 端已觸發事件，但我的 Bot 伺服器完全沒收到請求？**

      * **檢查清單**：
          * 確認你的 Bot 伺服器正在運行且網路通暢。
          * 檢查伺服器的防火牆是否開放了你設定的監聽連接埠 (e.g., 8000)。
          * 再次確認 WP 端的 `DISCORD_BOT_WEBHOOK_URL` 常數是否正確指向你的 Bot IP 和連接埠。

2.  **問題：我的 Bot 收到了請求，但在執行 Discord 操作時失敗 (例如無法刪除頻道)？**

      * **檢查清單**：
          * **權限問題**：這是最常見的原因。請確認 Bot 的身分組在 Discord 伺服器擁有必要的權限，例如「管理頻道」、「發送訊息」等。
          * **快取不一致**：在處理由 Webhook 觸發的快速、連續操作時（如剛建立就馬上要刪除），Bot 的內部快取可能與 Discord 的真實狀態不同步。在執行刪除等關鍵操作前，建議先使用 `await bot.fetch_channel(channel_id)` 來獲取一個「最新」的頻道物件，再對其進行操作。這可以有效避免因快取陳舊導致的權限誤判。

-----

## **5. 總結**

Bot 在這個整合中的角色是**高效的事件響應器**。它不需要處理客服單的業務邏輯，只需專注於接收來自 WordPress 的 Webhook 通知，並將其完美地呈現在 Discord 的使用者介面上。

反之，當有事件從 Discord 端發起時（例如你的團隊成員在頻道中回覆），則需要你的 Bot 去呼叫 WP 提供的 REST API 來同步資料。