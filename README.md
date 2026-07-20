# 世界移動|PChome 售價戰情板

以妳的《PChome售價試算.xlsx》為唯一資料源,每天自動抓取 PChome 商品即時售價、
對照浮動報價(成本),重算全部欄位並顯示在網頁儀表板。

## 運作流程

```
config/PChome售價試算.xlsx   ← 妳唯一需要維護的檔案
        │  (excel_to_config.py 讀取,含公式重現)
        ▼
config/products.json         全欄位資料 + 平台抽成設定
        │  (fetch_prices.py 每天抓 PChome 即時售價)
        ▼
data/latest.json + history.csv
        │
        ▼
index.html                   戰情板網頁(GitHub Pages)
```

## 專案結構

```
├── index.html                        儀表板網頁
├── config/PChome售價試算.xlsx         ★ 妳維護的 Excel(改報價/售價/新增品項都在這)
├── config/products.json              自動產生,勿手動編輯
├── scraper/excel_to_config.py        Excel → JSON(重現表內全部公式)
├── scraper/fetch_prices.py           PChome 即時售價抓取
├── data/latest.json                  最新結果(自動產生)
├── data/history.csv                  每日價格/報價歷史(自動累積)
└── .github/workflows/update-prices.yml   排程
```

## 一次性部署(約 10 分鐘)

1. GitHub 建立新 repository(建議 Public,Private 的 Pages 需付費方案)
2. 上傳整個資料夾內容(網頁版拖曳即可)
3. **Settings → Pages** → Source 選 `Deploy from a branch` → `main` / `(root)` → Save
4. **Actions** 分頁 → 啟用 → 點「每日更新市售價」→ **Run workflow** 手動跑第一次
5. 開啟 Pages 網址 `https://帳號.github.io/repo名/` 即可看到真實資料

之後每天台北時間早上 10:00 自動更新。

## Fastmove 浮動報價自動更新(Secrets 設定,一次完成)

系統每天會用 Playwright 模擬瀏覽器登入 Fastmove 發貨系統 → 我的報價 → 按「下載報價」
→ 解析匯出檔 → 以「加值方案」比對更新每列的浮動報價並重算所有欄位。

**帳密設定(只有 GitHub 加密保存,任何人與程式碼都看不到明文):**

1. repo → **Settings → Secrets and variables → Actions → New repository secret**
2. 新增兩筆:
   - Name:`FM_USER`,Secret:妳的 Fastmove 帳號
   - Name:`FM_PASS`,Secret:妳的 Fastmove 密碼
3. 完成。改密碼時回來更新 `FM_PASS` 即可

**比對規則:** Fastmove「商品名稱」=Excel「加值方案」(忽略空白;一格寫兩行方案時逐行嘗試,
取第一個對到的;`($21)` 之類尾註自動忽略)。已用妳的匯出檔實測:45 列全數對上。
對不上的列會沿用 Excel 報價,並在戰情板「報價來源」欄顯示 Excel。

**注意:** Fastmove 匯出檔約 8,000+ 筆全商品報價,系統只取妳 45 列用到的方案,其餘忽略。
若 Fastmove 後台改版導致抓取失敗,當天會沿用前次報價(workflow 不會中斷),
把 Actions 的錯誤訊息貼給 Claude 即可修。

## 日常維護:只改 Excel

- ~~供應商報價變動~~ → 已全自動(Fastmove 每日同步),K 欄不用再改
- 調售價 → 改 M 欄「售價」
- 新增品項 → 照原格式加一列(參考連結貼 PChome 商品網址,系統會自動抓該商品即時價)
- 平台費率變動 → 改右側「平台抽成設定」表

改完把 Excel 上傳回 repo 的 `config/` 覆蓋,**push 後會自動觸發重算**,不用等到隔天。

## 儀表板判讀

| 元素 | 意義 |
|---|---|
| 浮動報價 ▲紅 / ▼藍 | 供應商報價相較前次 上漲 / 下降 |
| 即時售價 ▲紅 / ▼藍 | PChome 商品頁目前售價相較前次 上漲 / 下降 |
| 「未取得」灰標 | 該列參考連結不是 PChome 商品網址,或當次抓取失敗 |
| 紅字利潤 | 單品利潤為負(售價低於成本結構),須調價 |
| 上方國家籤 | 快速篩選日本/韓國/越南/泰國/新馬/港澳/中國 |

## 注意事項

- 即時售價來自 PChome 非官方商品 API;若日後改版抓不到,把 Actions 的錯誤訊息貼給 Claude 即可修改 `fetch_prices.py`
- 抓取頻率為每天一次、每品項間隔 1.5 秒,屬低頻查詢
- 本機預覽:資料夾內執行 `python -m http.server` 後瀏覽 http://localhost:8000
