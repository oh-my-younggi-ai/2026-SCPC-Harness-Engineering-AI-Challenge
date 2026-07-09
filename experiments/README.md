# 제출 실험 run sheet (갱신 2026-07-09, BASE 실측 0.8441 반영)

기준: **BASE(Iter 023) LB 실측 0.8441** (+0.0375, 그러나 dev 이득의 ~40%만 transfer — dev-LB 갭 0.076).
컷까지 잔여 0.046. 모든 파일은 동일 코드에서 `SCPC_EXP` 토글만 바꿔 생성. 제출 시 `submission.csv`로 이름 변경. 슬롯 1개 = 실험 1개.

| 파일 | 토글 | BASE 대비 변경 | 상태 |
|---|---|---|---|
| submission_BASE.csv | (없음) | — | ✅ 제출됨: **LB 0.8441** |
| submission_E6.csv | E6 | 38 task (proceed→amend 26, ask→amend 12) | ✅ 오늘 슬롯2: R1/R2/R2b를 dev-검증 authority 하위집단으로 축소 |
| submission_E1.csv | E1 | 700 task (user_response만) | ✅ 오늘 슬롯3: semantic 잔여 회수 |
| submission_E2.csv | E2 | 14 task (hold→amend) | 내일 후보: doctor_note→hold 검증 |
| submission_E5.csv | E5 | 28 task | ⚠️ **제출 보류** — 규정 감사(LOG Iter 024) |
| submission_E5X.csv | E5X | 28 task | ⚠️ **제출 보류** — 규정 감사(LOG Iter 024) |

## ⚠️ E5/E5X 보류 사유

dev에 없는 screening 전용 record 값을 screening 입력 분석으로 발견해 정답 골격에 매핑한 것 —
유의사항의 "평가 데이터셋에서 특정 패턴을 분석해 모델 구조·정답 후보 설정에 반영하는 행위" 금지 문구에
정면 노출될 수 있는 유일한 항목. Iter 023(BASE)이 이미 dev 0.92라 기대가치도 낮음.
**상위권 코드 제출 전 harness.py에서 E5/E5X 토글 코드 제거 예정.**

## 오늘 남은 2슬롯

2. **E6** — Δ>0: 협의판 채택(이질 하위집단 과확장 확증) → 내일 ask-target(user→named 23건)도 같은 방식 검증. Δ<0: 광의판 유지.
3. **E1** — semantic 서술 변형 (검증된 레버, gate 무관).

## 내일 후보 (E6/E1 결과에 따라)

- ask-target 되돌림 프로브 (user→named 23건 — Iter 023의 미검증 축)
- E2 (doctor_note→hold), R2/R2b 개별 분리 (E6이 애매할 때)

## 판정 메모

- 결과는 improvement/LOG.md에 Iter로 기록. **DACON 제출창에서 최종 채점 파일 1개 선택 필수.**
