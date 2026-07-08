# 개선 후보 백로그 (2026-07-08 Iter 019 시점 최신화)

목표: LB 0.7933 → 0.89 (잔여 0.097). 구성: dev 천장(0.8303) ↑ + transfer 갭(0.037) ↓ + semantic(0.04, 미검증).

## 전략 원칙 (검증된 것)
1. **개념 수준 일반화**: dev-문자 규칙은 transfer 실패. 절/서사는 의미 계열(개념 어휘)로. (Iter 010/011 실증)
2. **screening 빈도 가중**: dev-희귀·screening-희귀(<1%) 신호는 스킵.
3. **중단-원천 원리**: 절(최신 지시)로 결정 ↔ record 신호로 결정이 target/클래스를 가르는 메타 패턴. (Iter 015/017)
4. 공짜 채점 bake-off로만 채택. 래칫(CV 0.8269) 하드게이트.

## 열린 후보 (우선순위순)

### 1. semantic_response 검증 [Iter 019 반영됨, 미검증]
- user_response를 클래스별 판단 서술로 교체함. **다음 제출에서 효과 분리 측정** (이번 제출의 유일한 변경).
- 오르면: 참조 응답 스타일에 더 정렬(간결/상세 변형 실험). 안 오르면 접기.

### 2. transfer 갭 0.037 — 재감사 완료(07-08 저녁), 구조 이상 없음
- 미매칭 절 0 · history_focal 237발화 · doctor_note 58/auth+guardrail 49 발화(dev 비례) · 분포 정합. **로컬에서 더 할 것 없음** — 잔여 갭은 semantic(0.04)과 클래스 잔여의 screening 버전 추정.

### 3. ~~plan 세부~~ → 소진 확인 (07-08 저녁)
- 게이트-내 plan 손실 = ask 하위이유 args 6건 + verb 2 + len 2뿐. 사실상 천장.

### 4. ~~scope allowed~~ → n=2 잔여, 스킵

## 신호 부재 확정 (재시도 금지 — attempts 참조)
- **ask 하위이유** (route vs precondition_changed, n=26): 중단원천×전제어휘 불분리. 다수결 route 유지. [07-08 확정]
- **ask mode 3분** (summary/redacted/none, n=23): 중단원천×boundary×sensitive 각도까지 소진. 다수결 summary 유지.
- **클래스 잔여 12**: 동일 신호→다른 클래스. payment/enterprise/ops recall류는 screening 2/700이라 스킵이 정답.
- **precondition_changed flag**: guardrail P=0.57 불충분.
- **other 클래스 mode** (n=7): raw/summary/redacted 혼합.

> 이 항목들이 dev 천장(~0.83)의 정체. 뚫으려면 생성기의 비가시 요소(확률적 변형 가능성)이거나 아직 못 본 파생 특징 필요.
