# OEE Platformu — Değer Önermesi

> **Kime yönelik:** Vardiya amiri, üretim müdürü  
> **Süre:** ~5 dakika okuma

---

## Problem: En büyük kaybınız nerede?

Her vardiya sonunda aynı soru kalır yanıtsız: "Bugün en çok nerede zaman / para kaybettik?"

- Duruş kayıtları saatler sonra Excel'e işlenir; o saatte karar almak için artık geç kalınmıştır.
- Mikro-duruşlar (30 sn – 5 dk arası) hiç kayıt altına alınmaz; toplamda önemli bir kütleye ulaşırlar.
- Hız kayıpları ve doluluk kayıpları çoğu zaman tamamen görünmezdir; kimse ölçmez.
- Sonuç: kayıp tahminleri ya yoktur ya da geriye dönük, haftalar sonra, bir toplantıda anlamlıdır — artık müdahale edemeyeceğiniz bir anda.

---

## Çözüm: Tek ekran, vardiya temposunda

Platform size **şu anda** şunu gösterir:

| Ne | Nasıl |
|----|-------|
| OEE (%) | Kullanılabilirlik × Performans × Kalite şelale grafiği |
| En büyük kayıp | O vardiyada sizi en çok etkileyen tek kalem, renkli vurgulu |
| TL karşılığı | "Bu kayıp, bu vardiyada ≈ X – Y TL'ye mal oldu" |
| Öneri | "Operatör bekleme süresi yüksek → besleyici hızını kontrol edin" |

Tek sayfa, gerçek zamanlı, tercüme gerektirmez. Sabah toplantısında projekte edin; ne üzerinde duracağınızı bilirsiniz.

---

## Neden güvenilir?

Platformun güven mimarisini şeffaf tutuyoruz — neyin ölçüldüğünü, neyin çıkarıldığını açıkça ayırırız.

**Görülen kayıplar (doğrudan ölçüm)**
- Duruş süresi: sensörden gelen sinyal kesildiğinde sayaç başlar.
- Mikro-duruş: operatör tarafından girilir (platformdaki tek manuel girdi).

**Çıkarılan kayıplar (model)**
- Gizli hız kaybı: hat nominal hızda değilken oluşan fark.
- Doluluk kaybı: hat çalışırken parça üretmediği süre.

Verinin azaldığı durumlarda (kısa vardiya, eksik sinyal) ilgili kalem otomatik olarak **"Düşük Güven"** rozeti alır. Sessizce yanlış bir sayı göstermeyiz; belirsizliği açıkça işaretleriz.

---

## Abartı yok

Kazanç tahminleri **üst sınır** olarak sunulur ve **aralık** biçimindedir (örn. "1.200 – 2.800 TL/vardiya"). Bunun nedenleri:

- Farklı kayıp kalemleri aynı durma süresini paylaşabilir; kalemlerin toplamı gerçek toplam kaybı aşabilir.
- Her kaybın üretim hattınızda ne kadar kurtarılabilir olduğunu yalnızca siz bilirsiniz.
- Biz kesin kazanç değil, **görünürlük** satıyoruz. Kararı ve önceliklendirmeyi size bırakıyoruz.

---

## Pilot size ne kazandırır?

~2 haftada, konuşmak yerine görmek:

1. **Daha önce bilinmeyen bir kaybı gün yüzüne çıkarın.** Vardiyada fark edilemeyen bir örüntü, grafikte anında görünür hale gelir.
2. **TL karşılığını sayısal olarak belgeleyin.** "Seziyoruz" yerine "X – Y TL/vardiya" diyebilirsiniz.
3. **Kararı veriye bağlayın.** Pilot boyunca hangi eylemin ne kadar etki yarattığını gözlemleyebilirsiniz.

Pilotta başarının nasıl ölçüleceğini netleştirmek için bkz. [05-basari-kriterleri.md](05-basari-kriterleri.md).

Canlı demo senaryosunu görmek için bkz. [02-demo-senaryosu.md](02-demo-senaryosu.md).

---

*Pilot kiti hakkında sorularınız için ekibimizle iletişime geçin.*
