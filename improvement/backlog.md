# 개선 후보 백로그 (기회 점수 내림차순)

데이터 기반. 게이팅 파급 고려. 노이즈 플로어 ≈ 0.034 (CV) — 이보다 큰 기대 이득 우선.

## ✅ Iter 001 완료: marker/route focal 해석 (focal 29%→89%, overall +0.203)

## 1. [최우선] decide_control 과다-"ask" 교정
- **근거**: focal-correct 107개 중 control 오답 다수가 "정답≠ask인데 ask로 예측" — proceed→ask 31, amend→ask 19, hold→ask 9 (계 59).
- **대상**: `decide_control`
- **가설**: `evidence.requires_confirmation` + ambiguous_*/amount_changed/routine_scope 트리거가 너무 광범위. 실제 신호(record value)를 더 좁게 봐야. proceed가 기본이어야 하는 경우를 ask로 오분류.
- **기대**: control↑ (0.275→). target도 맞은 task에서 scope/policy/plan 게이트 해제.

## 2. infer_target: memory_store / route 해석
- **근거**: target 오답 상위 — memory_store를 project_room/privacy_review 등으로 오예측(계 20+). `resolved_target`/route 신호 우선순위 문제.
- **대상**: `infer_target`
- **기대**: target↑ (0.392→). control과 함께 맞으면 downstream 해제.

## 3. content_scope / policy / plan 정교화
- focal·target·control 게이트가 더 열린 뒤 재진단(현재도 신호는 있으나 게이트 의존).

> 게이팅: scope/policy/plan은 target×control 둘 다 맞아야 점수. control(#1)과 target(#2)을 함께 올리는 것이 downstream 해제의 열쇠.
