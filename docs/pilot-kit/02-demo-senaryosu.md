# 02 — Rehberli Demo Senaryosu

> **Kitle:** Demo veren kişi (satış / portföy).  
> **Amaç:** Altı yerleşik demo senaryosuyla panoyu canlı olarak walk-through yapmak.

---

## 1. Demoyu Aç

### Standart yol (Docker)

```bash
docker compose up --build
```

Tarayıcıda `http://localhost:8000` adresini aç. Kimlik doğrulama kapalıysa doğrudan panoya düşersin.

> Render (bulut) kullanıyorsan kişisel Render URL'ini tarayıcıya yaz; adımlar aynı.

### Geliştirici alternatifi (native)

```bash
# Terminal 1 — backend
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

Frontend `http://localhost:5173` adresinde ayağa kalkar.

---

## 2. Rehberli Akış

Demo boyunca aşağıdaki adımları sırayla izle:

1. **Senaryo seç** — Sayfanın üstündeki dropdown'dan bir senaryo seç.
2. **Anlatı banner'ını oku** — Seçim sonrasında H6 başlık alanında kısa bir anlatı + **"neye bak"** ipucu belirir. Bunu sesli oku; dinleyiciye bağlamı ver.
3. **En büyük kaybı oku** — OEE kırılım ağacında (loss tree) en büyük kayıp kategorisini göster ve dakika / TL cinsinden değerini belirt.
4. **TL Pareto'ya bak** — "Maliyet Pareto'su" grafiğini aç. Hangi arıza/kayıp kategorisinin en fazla TL yaktığını göster.
5. **Öneriyi oku** — Pano, para birimi (TL) içeren bir öneri sunar. Metni yüksek sesle oku. "Düşük güven" rozeti olan önerilerde (H3 altındaki badge) veri çıkarımına dayandığını ve doğrulama gerektirdiğini belirt.
6. **Replay (isteğe bağlı)** — `/replay/stream` endpoint'ini tetikle. "Şimdiye kadar" anlık görüntüsünün vardiya ilerledikçe büyüdüğünü canlı olarak göster. Gerçek zamanlı izlemenin nasıl çalıştığını anlatmak için idealdir.

---

## 3. 6 Senaryo Anlatısı

| # | `id` | Başlık | Bir cümle anlatı | Odak grafik |
|---|------|--------|------------------|-------------|
| 1 | `baseline` | Normal hafta | Sıradan bir vardiya: kayıplar dengeli ama en pahalısı duruş — referans noktası. | Maliyet Pareto'su (`cost`) |
| 2 | `breakdown_storm` | Arıza fırtınası | Redresör ve vinç üst üste arızalanıyor; duruş kaybı tüm Pareto'yu domine ediyor. | Maliyet Pareto'su (`cost`) |
| 3 | `microstop_plague` | Mikro duruş salgını | Görünmez mikro duruşlar birikip büyük kayıp oluyor — operatör çoğunu hiç girmiyor. | Kayıp ağacı (`loss_tree`) |
| 4 | `speed_bottleneck` | Hız kaybı / darboğaz | Kaplama banyosu nominalden yavaş; kimse loglamıyor ama çıkarım hız kaybını yakalıyor. | Kayıp ağacı (`loss_tree`) |
| 5 | `fill_problem` | Doluluk problemi | Askılar yarı dolu gidiyor; kapasitenin önemli kısmı boşa — parça ekseninde dev kayıp. | Kayıp ağacı (`loss_tree`) |
| 6 | `redo_crisis` | Redo / kalite krizi | Kalınlık tutmuyor; parçalar tekrar tekrar kaplanıyor, ilk-geçiş kalitesi çöküyor. | Trend (`trend`) |

> **Not:** `baseline` senaryosu her zaman ilk gösterilir — dinleyiciye "normal" referans noktası verir. Ardından problem senaryolarına geç.

---

## 4. "Kendi Verinle"

Demo senaryoları yapay veriyle çalışır. Pilotu gerçek üretime taşımak için:

- Bkz. [03-veri-onboarding.md](03-veri-onboarding.md) — aynı pano, senin verinle.

Onboarding rehberi CSV şemasını, kolon eşlemeyi ve doğrulama adımlarını içerir.
