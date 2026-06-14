# Veri Sözleşmesi

Kaynak: sahadan/simülatörden gelen `*.csv`. Üç genel dosya platforma girer.
**Firewall:** `ground_truth.csv` ASLA ingest edilmez; yalnız ayrı doğrulama yolundan
okunur (G6). Platform verinin simülatörden mi sahadan mı geldiğini bilmez.

## events.csv
| alan | tip | not |
|------|-----|-----|
| timestamp | ISO datetime | olay başlangıcı |
| line_id | str | hat kimliği |
| station_id | str/boş | tank id / `HOIST` / hat seviyesinde boş |
| event_type | enum | LOAD, PROCESS, MOVE, UNLOAD, QC, OVER_RESIDENCE, DOWNTIME, MICROSTOP, STRIP |
| duration | float (dk) | olay süresi |
| reason_code | str/boş | DOWNTIME→otomatik kod; MICROSTOP→boş |
| operator_entered_reason | str/boş | operatör etiketi |
| operator_entry_ts | datetime/boş | operatör giriş zamanı |

## production.csv
| alan | tip | not |
|------|-----|-----|
| carrier_id | str | askı |
| order_id | str | iş emri |
| loaded_qty | int | yüklenen parça |
| good_count | int | sağlam |
| redo_count | int | yeniden işlenen (rework hacmi) |
| scrap_count | int | hurda |

Değişmez: `good_count + scrap_count == loaded_qty`. `redo_count` ayrı rework hacmidir.

## orders.csv
order_id, product_id, target_cycle, planned_qty.

## Hat tanımı (line definition)
`config/line_default.yaml` formatında: nominal tank süreleri, darboğaz, askı kapasitesi.
Quality/Performance kırılımı için gereklidir. Askı kapasitesi master-data'dır (firewall
arkasında değil).
