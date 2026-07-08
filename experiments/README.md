# 제출 실험 run sheet (생성일 2026-07-08, 기준점 LB 0.8066 = BASE)

모든 파일은 동일 코드(커밋 참조)에서 `SCPC_EXP` 토글만 바꿔 생성. 제출 시 파일을 `submission.csv`로 이름 바꿔 업로드.
리더보드는 결정적 채점 → Δ = 순수 신호. **슬롯 1개 = 실험 1개.**

| 파일 | 토글 | BASE 대비 변경 | 검증하는 가설 |
|---|---|---|---|
| submission_BASE.csv | (없음) | 0 | 기준점 (0.8066 재현용, 제출 불필요) |
| submission_E5.csv | E5 | 38 task (amend→proceed 26, ask→proceed 8, hold→proceed 4) | local-어휘 조합(boundary+auth/snap) = local 클래스 |
| submission_E5X.csv | E5X | 38 task (amend→proceed 38, E5와 다른 집합) | local_authority_confirmed 단독 = local |
| submission_E2.csv | E2 | 14 task (hold→amend) | doctor_note→hold 규칙이 틀렸는지 (dev n=2 근거) |
| submission_E1.csv | E1 | 700 task (user_response만) | semantic 서술에 target/scope 구체값·ontology 용어 포함 |

## 제출 순서 (3슬롯)

1. **E5** — Δ>0: local-어휘 가설 확증 → 2번은 E5X. Δ≤0: 2번은 E1.
2. **E5X 또는 E1** (1번 결과에 따라).
3. **E1 또는 E2** (남은 것 중 우선순위 높은 쪽; E1 미제출이면 E1).

## 판정 메모

- E5 Δ>0 & E5X Δ>E5: 단독 조건이 더 강함 → 조합 조건 폐기, E5X 채택.
- E1은 gate 무관(semantic 0.04 서버 전용) → Δ는 최대 ±0.04 범위, ±0.01 수준이어도 유의미.
- E2 Δ>0: doctor_note→hold 폐기. Δ<0: 규칙 확증(두면 됨). 실제 영향 14 task뿐이라 Δ는 작을 것.
- 결과는 improvement/LOG.md에 Iter로 기록하고 채택 토글은 기본 동작으로 승격(토글 제거).
