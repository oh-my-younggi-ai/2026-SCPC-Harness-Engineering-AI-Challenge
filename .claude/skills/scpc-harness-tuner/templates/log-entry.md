# SCPC Harness 개선 로그

> 매 반복: 가설 → 변경 → 점수 변화(before→after) → 결정. KEEP/REVERT 모두 기록.
> 채점 게이팅: focal 틀리면 target·control=0, target·control 틀리면 scope·policy·plan=0 (OVERVIEW §7).

| 지표 | 값 |
| --- | --- |
| 현재 overall (전체) | — |
| CV 일반화 평균±분산 | — |
| coverage % (handled/전체) | — |
| 활성 규칙 수 (풀 크기) | — |
| ratchet high-water (CV) | — |
| 누적 반복 수 | — |
| 최고 기록 (전체) | — |

---

<!-- 새 항목은 이 아래에 최신순으로 append -->

## Iter NNN — YYYY-MM-DD — [KEEP | REVERT]

**catalog 항목:** `<signal_id>`  ·  **지문:** `<대상메서드>:<signal_id>:<규칙종류>`

**가설:** (무엇을 바꾸면 어떤 항목/클러스터 N개가 회복되어 약 +Z 기대)

**변경 내용:** `rules/<signal>.py` (+`tests/test_<signal>.py`) — (사람이 읽을 수 있는 변경 설명. 어떤 신호→어떤 판단 규칙을 추가/수정했는지)

**점수 변화:**

| 축 | before | after | Δ |
| --- | --- | --- | --- |
| overall (전체) | | | |
| CV 일반화 평균 | | | |
| focal | | | |
| target | | | |
| control | | | |
| content_scope | | | |
| policy | | | |
| plan | | | |

**task 영향:** 고침 +N / 깨짐 −M (순 ±K)

**회귀 / 테스트:** 축적 단위테스트 (all green? ) · 래칫 (통과/위반) · 회귀 task id·원인 축(없으면 "없음")

**coverage:** X% → Y%

**결정:** KEEP / REVERT — (이유. 특히 CV 일반화·래칫이 어떻게 움직였는지)

**다음 후보:** (백로그 최우선, 기대 이득)

---
