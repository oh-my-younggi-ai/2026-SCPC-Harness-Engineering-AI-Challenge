# SCPC Harness 개선 로그

> 매 반복: 가설 → 변경 → 점수 변화(before→after) → 결정. 채점 게이팅: focal 틀리면 target·control=0, target·control 틀리면 scope·policy·plan=0 (OVERVIEW §7).

| 지표 | 값 |
| --- | --- |
| 현재 overall (전체) | 0.2911 |
| CV 일반화 평균±표준편차 | 0.2894 ± 0.0341 (k=5) |
| focal 정확도 | 89.2% (107/120) |
| 활성 규칙 수 (풀 크기) | 1 (marker_focal) |
| ratchet high-water (CV) | 0.2894 |
| 누적 반복 수 | 1 |
| 최고 기록 (전체) | 0.2911 |

**노이즈 관측(중요):** CV fold 표준편차 = **0.0358** (per-fold 0.043~0.136, 3배 스프레드). 즉 CV 기준 **~0.036 미만의 개선은 노이즈와 구분 불가**. 초기 focal 대형 개선은 이보다 크므로 감지 가능하지만, 미세 튜닝은 못 믿는다. → 포트폴리오 층(ablation/composition)은 이 노이즈 위에서 무의미하므로 **DEFERRED 유지**가 데이터로 확인됨.

---

## Iter 000 — 2026-07-07 — BASELINE

**변경 내용:** 주최 노트북(`SCPC2026_Final_baseline.ipynb`) 셀 1/3/5/7/9/11/16을 `harness/`로 verbatim 추출. `scpc_core.py`(고정 framework) + `harness.py`(FinalHarness, 개선 대상) + `run_local.py`(CV 오케스트레이터). 로직 변경 없음.

**재현성 검증:** 원본 노트북 셀13 실행 결과 = `overall 0.0882, focal 0.2917` → 추출본과 **정확히 일치**. (seed 2026→42는 meta 표기만, 결정적 출력에 무영향)

**점수(baseline):**

| 축 | 값 | 가중치 |
| --- | --- | --- |
| overall (전체) | 0.0882 | — |
| CV 일반화 평균 | 0.0880 ± 0.0358 | — |
| focal | 0.2917 | 0.18 |
| target | 0.1167 | 0.12 |
| control | 0.0833 | 0.18 |
| content_scope | 0.0196 | 0.17 |
| policy | 0.0087 | 0.13 |
| plan | 0.0126 | 0.18 |

**진단(데이터 관찰):** 전 축이 focal(29.2%) 게이트에 막혀 downstream이 near-zero. **focal 실패 85개 중 72개(85%)가 `marker_indirect`** — `focal_marker_refs`(marker→ref_code 매핑) + `focal_resolution_trace`로 후보를 간접 지시하는데 baseline `choose_focal`이 이를 처리하지 않음(직접 id / ref_code / 토큰겹침만 봄). TERMS_GUIDE §focal_marker_refs에 문서화된 메커니즘.

**다음 후보 (Iter 001):** `choose_focal`에 marker/route 해석 추가 → `marker_to_ref`로 marker를 object ref_code에 매핑, `focal_resolution_trace`로 따라갈 marker 선택 → 해당 object id를 focal로. **일반화 규칙**(특정 task_id 아님). 기대: focal ~29%→대폭 상승 + downstream 게이트 해제로 overall 노이즈플로어(0.036) 초과 상승 예상. 대상 메서드: `choose_focal`.

---

## Iter 001 — 2026-07-07 — KEEP

**catalog 항목:** `focal_marker_refs`  ·  **지문:** `choose_focal:focal_marker_refs:marker_route_resolution`

**가설:** marker 간접참조 미처리로 focal 실패 72/85. `choose_focal`에 marker→ref→object 해석을 추가하면 focal 대폭 회복 + downstream 게이트 해제.

**변경 내용:** `harness.py` `choose_focal` — 맨 앞에 `_resolve_marker_focal` 최우선 적용. 경로: `focal_resolution_trace.latest_phase` → `phase_to_marker[phase]` → marker → `focal_marker_refs.marker_to_ref[marker]` → ref_code → `attrs.ref_code` 일치 object. 일반화 규칙(하드코딩 없음). 사전 검증: dev marker task **83/83(100%)** 정확 해석. 단위테스트 `tests/test_marker_focal.py`(합성 입력) 추가·통과.

**점수 변화:**

| 축 | before | after | Δ |
| --- | --- | --- | --- |
| overall (전체) | 0.0882 | 0.2911 | **+0.2029** |
| CV 일반화 평균 | 0.0880 | 0.2894 | **+0.2014** (노이즈 0.036의 5.6배) |
| focal | 0.2917 | 0.8917 | +0.60 |
| target | 0.1167 | 0.3917 | +0.275 |
| control | 0.0833 | 0.2750 | +0.192 |
| content_scope | 0.0196 | 0.0697 | +0.050 |
| policy | 0.0087 | 0.0617 | +0.053 |
| plan | 0.0126 | 0.0792 | +0.066 |

**task 영향:** 고침 +72 / 깨짐 −0 (순 +72)

**회귀 / 테스트:** 축적 단위테스트 green · 래칫 통과(CV 0.088→0.289) · 회귀 task 없음

**coverage:** focal marker 신호 handled

**결정:** KEEP — CV 델타 +0.201이 노이즈 플로어(0.036)를 압도. 게이팅 캐스케이드 실증(focal 하나로 전 축 상승).

**다음 후보 (Iter 002):** `decide_control` 과다-"ask" 교정. focal-correct 107개 중 control 오답의 대부분이 정답이 ask가 아닌데 ask로 예측(proceed→ask 31, amend→ask 19, hold→ask 9 = 59). `requires_confirmation`/ambiguous_* 트리거가 너무 광범위. 병행: `infer_target` memory_store/route 해석(target 오답 다수). 대상: `decide_control`, `infer_target`.

---
