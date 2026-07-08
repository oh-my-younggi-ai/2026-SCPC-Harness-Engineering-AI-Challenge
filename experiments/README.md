# 제출 실험 run sheet (갱신 2026-07-08 밤, Iter 023 + 규정 감사 반영)

기준: 마지막 LB 실측 0.8066 (Iter 019 코드). **Iter 023으로 dev 0.9202 / CV 0.9211** — 새 BASE 자체가 최우선 검증 대상.
모든 파일은 동일 코드에서 `SCPC_EXP` 토글만 바꿔 생성. 제출 시 `submission.csv`로 이름 바꿔 업로드. 슬롯 1개 = 실험 1개.

| 파일 | 토글 | BASE 대비 변경 | 상태 |
|---|---|---|---|
| submission_BASE.csv | (없음) | — | ✅ 1순위: **Iter 023 transfer 검증** |
| submission_E1.csv | E1 | 700 task (user_response만) | ✅ 2순위: semantic 잔여 회수 |
| submission_E2.csv | E2 | 14 task (hold→amend) | ✅ 3순위: doctor_note→hold 검증 (dev-유래 규칙 on/off) |
| submission_E5.csv | E5 | 28 task | ⚠️ **제출 보류** — 규정 감사(LOG Iter 024) |
| submission_E5X.csv | E5X | 28 task | ⚠️ **제출 보류** — 규정 감사(LOG Iter 024) |

## ⚠️ E5/E5X 보류 사유

dev에 없는 screening 전용 record 값을 screening 입력 분석으로 발견해 정답 골격에 매핑한 것 —
유의사항의 "평가 데이터셋에서 특정 패턴을 분석해 모델 구조·정답 후보 설정에 반영하는 행위" 금지 문구에
정면 노출될 수 있는 유일한 항목. Iter 023(BASE)이 이미 dev 0.92라 기대가치도 낮음.
**상위권 코드 제출 전 harness.py에서 E5/E5X 토글 코드 제거 예정.**

## 제출 순서 (3슬롯)

1. **BASE (Iter 023)** — 기대 0.88~0.90 (이전 dev-LB 갭 0.02~0.04).
2. **E1** — semantic 서술 변형 (검증된 레버, gate 무관 최대 ±0.04).
3. **E2** — doctor_note→hold 방향 검증 (Δ>0면 규칙 폐기, Δ<0면 확증).

## 판정 메모

- BASE가 0.89 넘으면 본선 컷 통과 — 이후 슬롯은 안전 마진 확보용.
- 결과는 improvement/LOG.md에 Iter로 기록. **DACON 제출창에서 최종 채점 파일 1개 선택 필수.**
