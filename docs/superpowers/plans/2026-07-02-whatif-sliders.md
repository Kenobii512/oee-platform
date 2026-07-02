# What-if Slider'ları Implementation Plan

> **Spec:** `docs/superpowers/specs/2026-07-02-whatif-sliders-design.md`. TDD; her görev ayrı commit.

**Goal:** `GET /whatif` (analitik önce→sonra + TL kazanç) + pano Detay'da WhatIf paneli.

## Task 1: `app/analytics/whatif.py` + `GET /whatif` (TDD)

- [ ] Testler önce (`tests/test_whatif.py`): sıfır azaltım = compute_oee baseline'ı ile birebir;
  yalnız downtime azaltımı → A yükselir, P/Q sabit; speed → yalnız P; redo → yalnız Q;
  fill → OEE sabit, TL kazanç > 0; clamp'ler (p=1.0'da A ≤ 1); TL = Σ tl·p (+bant);
  boş veri → sıfırlar; endpoint 200 şekli + geçersiz oran → 400.
- [ ] `compute_whatif(events, production, line, cost_tree, reductions) -> dict` —
  availability_from_events/nominal_full_pass/üretim toplamları yeniden kullanılır
  (formüller spec'teki gibi; kopya metrik mantığı YOK, aynı yardımcılar).
- [ ] `app/api/whatif_routes.py`: query paramları (5 kategori, vars. 0.0) + validate_range;
  route içinde loss_tree+to_tl mevcut desenle (cost_routes ikizi). main.py include.

## Task 2: `frontend/src/components/WhatIf.tsx`

- [ ] types.ts `WhatIf*` tipleri + client `api.whatif(reductions, range)`.
- [ ] Bileşen: 5 slider (0–50, step 5) + değer rozetleri; 300ms debounce'lu sorgu;
  önce→sonra satırı (A/P/Q/OEE, delta ok+renk) + kazanç aralığı (`tl_low–tl_high`);
  "Önerilen değerler" (recommend oranları — recQ verisinden `recovery_ratio`) + "Sıfırla";
  çekince metni. Dashboard Detay'da "What-if" zone (Aksiyon'dan sonra).
- [ ] vitest: render + slider değişimi sorgu parametresine yansır (msw yok — fetch mock).

## Task 3: Doğrulama + PR

- [ ] pytest tam + ruff + tsc + eslint + vitest + build + frontend-sync; Playwright görsel tur
  (slider kaydır → değerler değişir ekran görüntüsü).
- [ ] STATUS.md satır + API yüzeyi; README gezinti gerekirse. PR → CI → merge → memory.
