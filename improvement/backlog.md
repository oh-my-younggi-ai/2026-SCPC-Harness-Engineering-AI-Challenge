# 개선 백로그 (2026-07-08 밤, LB 0.8066 시점)

목표: **0.8066 → 0.89 (잔여 0.083)**. 추정 구성: semantic 잔여 ~0.01 + transfer 잔여 ~0.05 + dev 잔여(0.17, 대부분 신호부재).
원칙: 로컬 신호 소진 → **제출 1슬롯 = 단일변수 실험 1개** (하루 3슬롯 = 질문 3개). 개념 일반화·래칫·bake-off 규율 유지.

## 🔑 핵심 발견 (07-08 밤): screening 전용 record 어휘
사용자 직감("카테고리 통째 누락?")이 적중 — **screening에 dev에 없는 record 값들이 대량 존재**:
`dispatch_authority_check=local_authority_confirmed` **104개(15%)** · `route_candidate_snapshot=local_candidate_only` 65 / `mixed_local_external_candidates` 177 · `share_boundary_update=redacted_after_selection_boundary` 73 · `route_binding_order=candidates_after_authority` 207.
dev-정확일치 분류라 전부 fallback(minimal)로 추락 중 → **local 분류율 22% vs dev 33% 결손의 원인 후보.** 값 이름은 자기서술적(생성기 온톨로지)이나 dev로 검증 불가 → LB 실험으로만 판정. 0.85~0.87 군집과의 갭(-0.05)과 크기 일치.

## 실험 큐 (내일 3슬롯 — 우선순위순, LB는 결정적 채점이라 델타=신호)

### E5. [신규 최우선] screening local-어휘 매핑 (토글 구현됨: SCPC_EXP=E5)
- 규칙: 절-없음 + boundary=local_update_boundary + (auth=local_authority_confirmed or snap=local_candidate_only) → local (38 task 이동).
- 방증: E5 적용 시 screening 분포가 dev 비율로 접근 (local 22→28%, minimal 36→30%). Δ>0면 local_authority_confirmed 단독(104개)으로 확대 실험.

### E1. user_response 변형 (검증된 레버, 잔여 ~0.01)
- 현재: 클래스별 고정 서술. 변형 후보: (a) target/scope 구체값 포함형 ("summary만 project_room으로…") (b) 사유 키워드 강화형 (전제 무효화/route 미확정 등 ontology 용어 직접 사용).
- 설계: 변형 (a) 단독 제출 → Δ로 방향 확인. 오르면 (b) 추가.

### E2. doctor_note→hold 방향 검증 (토글 구현됨: SCPC_EXP=E2로 규칙 off) (screening 58개 적용 중, dev 근거 n=2뿐)
- 위험: dev 2건으로 일반화한 규칙이 58건에 적용 중. 틀렸다면 -0.01~0.04 손실 중일 수도.
- 설계: 이 규칙만 끈(→minimal/amend) 버전 제출. Δ>0면 규칙 폐기, Δ<0면 규칙 확증. 어느 쪽이든 정보 +.

### E3. auth_incomplete+guardrail→hold 검증 (screening 49개, dev 6/6)
- E2와 같은 구조. dev 근거는 6/6이라 E2보다 신뢰 높음 — E2 결과 보고 결정.

### E4. ask mode 실험 (dev 다수결 summary 12/23)
- screening의 ask 161개에 summary 일괄 적용 중. redacted 버전과 비교 실험 가능. 우선순위 낮음(mode는 scope 점수의 0.4×0.17 국소).

## 로컬에서 가능한 것 (제출 불요)
- L1. user_response 변형안 (a)(b) 작성 자체 — 문구 설계는 로컬 작업.
- L2. E2/E3용 토글: ruleset/플래그로 규칙 on/off 가능하게 소규모 리팩터 (실험 제출 준비).
- L3. 클래스 잔여 12에 대한 마지막 각도: personal_memory 텍스트/objects 구성 — 아직 안 본 필드 조합이 남았는지 30분 한도로 확인.

## 신호 부재 확정 (재시도 금지 — attempts 참조)
- ask mode 3분(n=23) · ask 하위이유(n=26) · 클래스 잔여 12(record/prompt/guardrail/vh서사 전부 소진) · precondition_changed flag · other mode(n=7) · vh 서사유형(전체 27~58% 순도)

## 검증된 전략 원칙
1. 개념 수준 일반화 (Iter 010/011) 2. screening 빈도 가중 3. 중단-원천 원리 (015/017) 4. bake-off+래칫 5. **제출=단일변수 실험** (019 실증)
