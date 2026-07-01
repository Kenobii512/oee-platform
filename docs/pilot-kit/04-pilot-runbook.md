# 04 — Pilot Runbook

> **Kapsam:** Kaplama hattı pilotu için ~2 haftalık oyun kitabı.  
> Hem tedarikçi (vendor) ekibinin hem de müşteri ekibinin başvuru belgesidir.

---

## Genel Bakış

Pilot, yaklaşık iki haftalık bir süreçte üç canlı aşamadan oluşur: kickoff günü kurulum ve hat tanımlaması tamamlanır; ardından ~2 hafta boyunca üretim verisi periyodik olarak sisteme yüklenir ve OEE tablosu izlenir; son olarak bir gözden geçirme toplantısıyla başarı kriterleri değerlendirilir ve bir pilot raporu hazırlanır. Tüm karar noktaları aşağıdaki faz yapısında belgelenmiştir.

---

## Fazlar

### Faz 0 — Hazırlık (Kickoff, ~1 Gün)

**Hedef:** Sistemi üretime hazır hâle getirmek ve ilk veri örneğini almak.

| Adım | Açıklama | Sorumlu |
|------|-----------|---------|
| 0.1 Hat tanımı | Üretim hattını tanımla; `POST /line/validate` isteği göndererek yanıtın `{"valid": true, "errors": []}` döndüğünü (tam olarak 1 darboğaz vb.) doğrula. Aynı doğrulama **Pilot Doctor**'ın `line` kontrolü olarak da koşar (aşağıya bakın). | Tedarikçi |
| 0.2 Örnek ham dışa aktarım | Müşteriden **bir adet** örnek ham veri dışa aktarımı al (CSV / Excel). | Müşteri |
| 0.3 Adaptör profili oluştur | Alınan örneği kullanarak H2 adaptör profilini inşa et. Bkz. [03-veri-onboarding.md](03-veri-onboarding.md). | Tedarikçi |
| 0.4 Dağıtım | H9 adımına göre Render veya Docker ile sistemi dağıt. | Tedarikçi |

---

### Faz 1 — Smoke Testi (~1–2 Gün · **GO/NO-GO KAPISI**)

**Hedef:** Sistemin gerçek veriyle uçtan uca çalıştığını kanıtlamak.

#### İşlem Adımları

1. Örnek dosyayı aşağıdaki istek ile yükle:

   ```http
   POST /ingest
   Content-Type: application/json

   {
     "path": "<örnek-dosya-yolu>",
     "adapter": "<adaptör-profil-adı>"
   }
   ```

2. Dashboard'un açıldığını doğrula.
3. `/oee` endpoint'inin **anlamlı** (sıfır olmayan, %0–100 aralığında) bir değer döndürdüğünü kontrol et.
4. **Veri-yeterliliği skorunun (H3) eşiğin üzerinde** olduğunu doğrula.
5. Reddedilen satır oranının kabul edilebilir sınırın altında olduğunu kontrol et.

#### Karar Noktası

| Sonuç | Eylem |
|-------|-------|
| **GO** ✅ | Tüm kontroller geçti → Faz 2'ye geç. |
| **NO-GO** ❌ | Adaptörü veya kaynak veriyi düzelt ve Faz 1'i yeniden çalıştır. |

#### Otomatik Kapı: Pilot Doctor CLI

Bu kapı artık **tek komutla otomatik** çalışır:

```bash
cd backend && python -m tools.pilot_doctor <veri-dizini> --adapter <profil-adı>
```

Araç, Faz 0–1 kontrollerini (hat doğrulama, adaptör eşlemesi, smoke ingest, OEE
anlamlılığı, H3 yeterlilik skoru, reddedilen satır oranı) sırayla koşar ve tek bir
**GO / NO-GO** raporu üretir. Çıkış kodu: `0` = GO, `1` = NO-GO, `2` = kullanım hatası.
Otomasyon/CI için `--json` bayrağı makine-okur çıktı verir. İngest tamamen **geçici**
bir veritabanına yapılır; gerçek sisteme dokunulmaz — kapıdan geçince gerçek yüklemeyi
`POST /ingest` ile yapın.

> **Eşikler:** Doctor'ın varsayılanları bu runbook ile aynıdır: yeterlilik ≥ **0.6**
> (`--min-sufficiency`), red oranı ≤ **%5** (`--max-reject`). Not: `config/confidence.yaml`
> içindeki `sufficiency_threshold: 0.5` **panodaki "düşük güven" rozetinin** eşiğidir —
> pilot kapısından ayrı bir amaca hizmet eder, karıştırmayın.
>
> **Örnek veri boyutu:** Faz 1'de kullanılan örnek dışa aktarım **en az bir tam vardiyayı**
> kapsamalıdır; birkaç satırlık mini örnek, veri-yeterlilik kontrolünden (H3) doğal olarak
> geçemez.

---

### Faz 2 — Veri Toplama (~2 Hafta)

**Hedef:** Yeterli üretim verisi biriktirerek anlamlı bir trend elde etmek.

| Görev | Açıklama | Sorumlu |
|-------|-----------|---------|
| Periyodik dışa aktarım | Müşteri, vardiya veya gün sonu verilerini düzenli olarak dışa aktarır (manuel ya da zamanlanmış). | Müşteri |
| Periyodik ingest | Tedarikçi veya zamanlanmış bir betik, her dışa aktarım için `POST /ingest` çağrısı yapar. | Tedarikçi / Otomasyon |
| Dashboard izleme | OEE, Kullanılabilirlik, Performans ve Kalite trendleri günlük olarak gözlemlenir. | Her iki taraf |

---

### Faz 3 — Gözden Geçirme Toplantısı (Gün ~14)

**Hedef:** Pilot verilerini başarı kriterleriyle karşılaştırmak ve ilerleme kararı almak.

1. Toplanan OEE verisini üç başarı kriteri karşısında değerlendir. Bkz. [05-basari-kriterleri.md](05-basari-kriterleri.md).
2. **Pilot raporu** hazırla.

> **Not:** Rapor artefakt şablonu, alt proje C (showcase) kapsamında sağlanacaktır.

---

## Roller

| Görev Alanı | Tedarikçi (Vendor) | Müşteri |
|-------------|---------------------|---------|
| Kurulum & Dağıtım | Hat doğrulama, adaptör profili oluşturma, sistem dağıtımı | — |
| Veri Akışı | Ingest işlemleri, adaptör bakımı | Ham veri dışa aktarımı, hat üretim bilgisi sağlama |
| İzleme & Analiz | Dashboard yorumlama, anomali tespiti | Dashboard'u takip etme, operasyonel bağlam sağlama |
| Gözden Geçirme Toplantısı | Analiz sunumu, pilot raporu hazırlama | Karar alma, iş etkisi değerlendirme |

---

## Zaman Çizelgesi Şablonu

Aşağıdaki tablonun **Tarih** sütununu projeye göre doldurun.

| Gün | Etkinlik | Tarih |
|-----|----------|-------|
| Gün 1 | **Kickoff:** Hat tanımı, örnek veri alımı, adaptör profili, dağıtım (Faz 0) | `____-__-__` |
| Gün ~3 | **Smoke GO/NO-GO:** Örnek ingest, dashboard + `/oee` doğrulama, H3 skoru kontrolü (Faz 1) | `____-__-__` |
| Günler 3–14 | **Veri Toplama:** Periyodik dışa aktarım & ingest, dashboard izleme (Faz 2) | `____-__-__ – ____-__-__` |
| Gün 14 | **Gözden Geçirme Toplantısı:** Başarı kriteri değerlendirme, pilot raporu (Faz 3) | `____-__-__` |

---

*İlgili belgeler: [03-veri-onboarding.md](03-veri-onboarding.md) · [05-basari-kriterleri.md](05-basari-kriterleri.md)*
