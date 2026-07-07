# 개선 후보 백로그 (기회 점수 내림차순)

데이터 기반. 게이팅 파급 고려. 노이즈 플로어 ≈ 0.02~0.03 (CV, Iter 002서 분산 감소) — 이보다 큰 기대 이득 우선.

## ✅ 완료
- Iter 001: marker/route focal 해석 (focal 29%→89%, overall +0.203)
- Iter 002: decide_control ask 트리거 정제 (control 0.275→0.400, overall +0.051)

## 1. [최우선] infer_target: memory_store / route target 해석
- **근거**: focal-correct 107개 중 target 오답 상위 = `memory_store`를 project_room/privacy_review/legal_review 등으로 오예측(25+). `user` 오예측도.
- **대상**: `infer_target`
- **가설**: `infer_target`이 memory_store를 `persistent_memory_write` 존재에만 의존. `persistent_memory_recall`/memory 관련 신호, resolved_target의 route 값 우선순위를 넓혀야. attrs.recipient(표면 수신자)를 resolved_target보다 우선하는 현 순서도 의심.
- **기대**: target 0.392↑. control과 함께 맞은 task에서 scope/policy/plan 추가 해제.

## 2. true-ask 17개 정밀 분리 (Iter 002 회귀 복구)
- **근거**: Iter 002서 ambiguous_* 라벨 제거로 진짜 ask 17개가 proceed/amend로 떨어짐.
- **문제**: ambiguous_target 값이 true/false-ask 동일 → 라벨로 분리 불가. **다른 신호 필요**(surface recipient vs resolved_target 불일치 정도, target_changed 조합, visible_history 등).
- **주의**: 해결 시 false-ask 재발 없이 순증 되는지 공짜 채점으로 검증 필수.

## 3. content_scope / policy 정교화
- focal·target·control 게이트가 더 열린 뒤 재진단. 현재 scope 0.134/policy 0.119 — allowed/excluded_fields F1, risk_flags/violations 정밀화 여지.

> 게이팅: scope/policy/plan은 target×control 둘 다 맞아야 점수. 지금은 control이 0.40으로 올랐으니 target(#1)을 올리면 downstream이 크게 열린다.
