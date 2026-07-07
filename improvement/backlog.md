# 개선 후보 백로그 (기회 점수 내림차순)

데이터 기반. 게이팅 파급 고려. 노이즈 플로어 ≈ 0.036 (CV) — 이보다 큰 기대 이득 우선.

## 1. [최우선] marker/route 간접참조 focal 해석
- **근거**: focal 실패 85개 중 **72개(85%)** 가 `focal_marker_refs`+`focal_resolution_trace` 미처리.
- **대상**: `choose_focal`
- **규칙**: `focal_marker_refs.marker_to_ref`로 marker→ref_code, `focal_resolution_trace`로 현재 따라갈 marker 선택 → object.id를 focal로. 일반화 규칙(하드코딩 아님).
- **기대**: focal 대폭↑ + downstream(target/control/scope/policy/plan) 게이트 해제. overall 노이즈플로어 초과 예상.

## 2. focal 후보가 많은 task (5~10 objects)
- **근거**: many_objects 미스 ~10개. marker 처리 후 잔여 확인 필요.
- **대상**: `choose_focal` (marker 없을 때 fallback 순위)

## 3. ambiguous_focal 처리
- **근거**: ambiguous_focal 미스 2개(소수). marker 처리 후 재측정.

> target/control/scope/policy/plan 후보는 focal 게이트가 열린 뒤 재진단한다(현재는 near-zero라 신호 없음).
