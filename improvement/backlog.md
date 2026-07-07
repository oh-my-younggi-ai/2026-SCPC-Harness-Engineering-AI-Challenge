# 개선 후보 백로그 (기회 점수 내림차순)

데이터 기반. 게이팅 파급 고려. 노이즈 플로어 ≈ 0.02~0.03 (CV, Iter 002서 분산 감소) — 이보다 큰 기대 이득 우선.

## ⚠️ 전략 원칙 (Iter 002 후 점검서 도출)
**노력을 dev 빈도가 아니라 screening 빈도로 가중하라.** dev 120 vs screening 700 신호 분포:
- 지배 신호(transfer 잘 됨): `focal_marker_refs` 66%, `resolved_target` 68%, `ambiguous_target` 41%(dev 22%의 2배!), `ambiguous_focal` 18%.
- 희귀 신호(dev 전용, screening <1%): `persistent_memory_write` 0.6%, `security_alert` 0.4%, `consent` 1.1%, `target_changed_after_turn` 0.6%. `amount_changed`/`merchant_verification`은 **어디에도 0%**(inert).
- 함의: 희귀 record 기반 규칙은 리더보드를 못 움직인다. 지배 신호에 집중.
- Iter 002 주의: ambiguous_target을 ask서 뺐는데 screening엔 2배 → transfer 불확실(dev fold 5/5 일관이나 분포 shift는 별개).

## ✅ 완료
- Iter 001: marker/route focal 해석 (focal 29%→89%, overall +0.203)
- Iter 002: decide_control ask 트리거 정제 (control 0.275→0.400, overall +0.051)

## 1. [최우선] infer_target: 지배적 route 경로 해석 (memory_store 아님)
- **근거**: focal-correct 107개 중 target 오답 상위 = `memory_store` 오예측(25+). **단, `persistent_memory_write`는 screening 0.6%(희귀)** → memory_store 자체는 dev 편중. 리더보드 이득은 지배 신호에서 나와야.
- **대상**: `infer_target`
- **수정된 가설**: memory_store 특수처리보다 **`resolved_target`(screening 68%)의 route/target 값 해석과 우선순위**를 정교화. 현재 attrs.recipient(표면 수신자)를 resolved_target보다 뒤에 두는지/앞에 두는지 순서 검증. 지배 신호 기반이라 transfer 기대.
- **검증**: dev target 오답을 memory_store 케이스(dev편중)와 route/recipient 케이스(지배)로 분리해 후자에 집중. 공짜 채점으로 순증 확인.

## 2. true-ask 정밀 분리 (Iter 002 회귀 복구 + screening 대비)
- **중요도 상향**: `ambiguous_target`이 screening 41%(dev 2배). Iter 002의 "ask 트리거 제거"가 screening서 진짜 ask를 대량 놓칠 위험. **진짜 ask 신호를 찾는 게 dev 회귀 17개 + screening 둘 다 사는 길.**
- **문제**: ambiguous_target 값이 true/false-ask 동일. 다른 신호 필요(surface recipient vs resolved_target 불일치 정도, visible_history, target_changed 조합).
- **주의**: 해결 시 false-ask 재발 없이 순증 되는지 공짜 채점으로 검증 필수.
- **근거**: Iter 002서 ambiguous_* 라벨 제거로 진짜 ask 17개가 proceed/amend로 떨어짐.
- **문제**: ambiguous_target 값이 true/false-ask 동일 → 라벨로 분리 불가. **다른 신호 필요**(surface recipient vs resolved_target 불일치 정도, target_changed 조합, visible_history 등).
- **주의**: 해결 시 false-ask 재발 없이 순증 되는지 공짜 채점으로 검증 필수.

## 3. content_scope / policy 정교화
- focal·target·control 게이트가 더 열린 뒤 재진단. 현재 scope 0.134/policy 0.119 — allowed/excluded_fields F1, risk_flags/violations 정밀화 여지.

> 게이팅: scope/policy/plan은 target×control 둘 다 맞아야 점수. 지금은 control이 0.40으로 올랐으니 target(#1)을 올리면 downstream이 크게 열린다.
