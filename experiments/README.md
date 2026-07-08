# 제출 실험 run sheet (갱신 2026-07-08 밤, Iter 023 반영)

기준: 마지막 LB 실측 0.8066 (Iter 019 코드). **Iter 023으로 dev 0.9202 / CV 0.9211** — 새 BASE 자체가 최우선 검증 대상.
모든 파일은 동일 코드에서 `SCPC_EXP` 토글만 바꿔 생성. 제출 시 `submission.csv`로 이름 바꿔 업로드. 슬롯 1개 = 실험 1개.

| 파일 | 토글 | BASE 대비 변경 | 검증하는 가설 |
|---|---|---|---|
| submission_BASE.csv | (없음) | — | **Iter 023 transfer** (값-조합 규칙 + target 중단-원천 확장) |
| submission_E5.csv | E5 | 28 task (ask16/amend8/hold4→proceed) | local-어휘 조합 = local (R1 미포섭분) |
| submission_E5X.csv | E5X | 28 task (amend16/ask8→proceed) | local_authority_confirmed 단독 = local |
| submission_E2.csv | E2 | 14 task (hold→amend) | doctor_note→hold 규칙 검증 (dev n=2) |
| submission_E1.csv | E1 | 700 task (user_response만) | semantic 서술에 구체값·ontology 용어 |

## 제출 순서 (3슬롯)

1. **BASE (Iter 023)** — 대형 변경의 transfer 측정이 최우선. 기대 0.88~0.90 (이전 dev-LB 갭 0.02~0.04).
2. BASE Δ 크면(≥+0.06): **E1** (semantic 잔여 회수, 검증된 레버). BASE Δ 작으면(<+0.04): transfer 실패 요소 분석이 우선이므로 **E5** (독립 가설 검증).
3. 남은 것 중 우선순위: E5 → E5X → E2.

## 판정 메모

- BASE가 0.89 넘으면 본선 컷 통과 — 이후 슬롯은 안전 마진 확보용.
- E5/E5X Δ>0면 해당 조건을 기본 규칙으로 승격. E2 Δ>0면 doctor_note→hold 폐기.
- 결과는 improvement/LOG.md에 Iter로 기록.
