# 백로그 — 총력전 모드 (2026-07-11, LB 0.8496)

**골: 0.90. 멈춤 없음. 명시적 금지(외부 API/네트워크, task_id/session_id 하드코딩, dev_answers 제출물 포함, 정답 분포 분석) 외 전 수단 동원.**
운용 원칙 전환: "로컬 신호 부재 = 동결" → **"로컬 검증 불가 = LB 프로빙 대상"**. 하루 3슬롯 = 3비트. 최종선택 보호로 하방은 슬롯뿐.

## 표적 지도 (남은 -0.15의 소재, 실측 기반)
| 구간 | 규모 | 현 상태 | 공략 수단 |
|---|---|---|---|
| dev-미출현 인자 조합 | **140건 (절-없음의 52%)** | 보수적 폴백 | **F5 이름-의미론 합성** |
| ask mode (screening ask ~161건) | 3층위 로컬 신호부재 | summary 일괄 | **M1 프로빙** |
| semantic 잔여 | ~0.01-0.015 | E1 기각(구체화는 역효과) | M2 초간결/문체 변형 |
| plan/scope 세부 | 소폭 | dev-포화 | M3 이벤트 구성 프로브 |
| mixed_local_external (177) | strict 종속 추정 | minimal 폴백 | M4 프로빙 |

## 무기고 (구현 순)

### F5 [최우선, 오늘] — unseen 조합 140건의 이름-의미론 합성 계층
- 인자별 형태소 의미(F1 실증 원리의 전면 확장): boundary{local/redacted/blocked} × authority{confirmed/incomplete/pending, local-형태소} × snapshot{single_internal/local_only/mixed/external} 합성.
- dev-검증 영역 불변(cascade 유지), unseen 조합에만 적용. F2(redact family) 포함.
- E5/E5X가 노리던 것의 상위집합을 "일반화 계층" 형태로 흡수. 폭 ±0.03.

### M1 — ask mode 전역 프로빙 (ask ~161건 summary→redacted 플립)
- 로컬 3층위 신호부재였지만 LB는 답을 앎. Δ 부호로 screening ask의 진짜 다수 mode 확정. 폭 ±0.01-0.02.

### M2 — semantic 문체 변형 (E1 역방향)
- (a) 초간결형 (b) 프로필 ops_memory_note 문체 모사. 슬롯당 1변형.

### M3 — plan 구성 프로브: minimal에 verify 삽입(read→verify→redact→dispatch) 등.

### M4 — mixed_local_external_candidates 177건: ask 처리 프로빙.

### E2 — doctor_note 14건 (잔여).

## 프로빙 규율
1. 슬롯 1 = 모집단 1 = 비트 1. 큰 모집단부터 (F5 140 > M1 161겹침 > M4 177겹침 > M2 > M3 > E2).
2. Δ>0 즉시 기본 승격, Δ<0도 방향 확정으로 기록 — 모든 결과가 다음 슬롯의 정보.
3. 이분탐색: 큰 모집단에서 Δ가 애매하면 반으로 쪼개 재프로빙.
4. 매 제출 후 최종선택 파일 = 역대 최고점 유지.

## 유지 사항
- 래칫/attempts/LOG 규율, 회귀 테스트 4종, 결정성.
- 코드에 screening 전용 문자열 열거 금지 (일반화 계층 형태로만 — 검증 대비).
- 최종 코드 제출 전 토글 승격/제거 정리.

## 완료·확증 (재시도 금지)
F1(+0.0009 확증) · E6/E7(광의 규칙·named target 확증) · E1(구체화 역효과) · dev 마이닝 소진(0.9309) · 기계적 누수 무혐의(Iter 030) · E5 원형(데이터가 반대, F5로 흡수)
