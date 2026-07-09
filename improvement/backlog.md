# 개선 백로그 (2026-07-09 밤, LB 0.8456 시점)

목표: **0.8456 → 0.89 (잔여 0.0434)**. 최종선택 파일 = BASE v2 (0.8456).
상태: dev 0.9256 / CV 0.9264. dev-LB 갭 ~0.080, transfer율 하락 추세 (023: 42% → 026: 28%).
텔레메트리 결론 (LOG Iter 027): 갭은 단일 버그가 아니라 **"dev 근거 극소 × screening 질량 대량" 경로들에 분산** — cl_redact(n=2→72), cl_confirm(11→119), cl_invalid(6→88), focal-history(22→237).

## 솔직한 전망
확인된 레버 합계 추정: E1 +0.005~0.01, E7 ±0.01~0.02(방향 미지), 로컬 판별자 발굴 +0.005/건.
**0.89 도달은 좁은 길** — E7이 양수(ask-target이 틀렸던 경우 +0.02)로 터지거나 history/clause 감사에서 실질 버그가 나와야 함. 남은 슬롯을 정보 최대화로 운용.

## 내일(07-10) 3슬롯 계획

### S1. E7 — ask-target named-fallthrough 되돌림 (37 task, user로 회귀)
- Iter 023 구성요소 중 마지막 미검증 축. dev는 -0.031이지만 screening ask 분포가 다르면 역전 가능.
- Δ>0: fallthrough 폐기(+점수 회수), Δ<0: 확증. 어느 쪽이든 037건의 방향 확정.
- ⚠️ v2 코드 위에서 재생성 필요 (`SCPC_EXP=E7`).

### S2. E1 — user_response 구체값+ontology 용어형 (700 task, semantic만)
- 검증된 레버의 변형. v2 위에서 재생성됨 (`experiments/submission_E1.csv`).

### S3. (S1/S2 결과 보고) 승자 조합판 or E2(doctor_note 14건)
- E7·E1 모두 양수면 조합판(효과 가산 — 접촉 축 분리 확인됨)이 최종 후보.

## 로컬 작업 (제출 불요, 우선순위순)

### L5. [신규 1순위] focal-history 서사 감사 (screening 237건, 하드게이트)
- dev n=22 정확도 1.00이 10× 질량에 얹혀 있음. screening에서 designation 패턴이 **복수 객체에 매칭되거나 서수-결합이 애매한** task 수를 계수 → 모호 사례의 해석 규칙 강건화.
- focal은 하드게이트: 5% 오류 = -0.015.

### L6. [신규 2순위] clause 하위-답안 감사 (screening 432건, 62%)
- 클래스는 골격이 정하지만 target/scope 세부는 클래스 기본값 — dev의 절-보유 task에서 기본값 이탈 사례(예: cl_local인데 target≠memory_store)를 마이닝해 조건 발굴. cl_redact(n=2)의 excluded_fields 다양성도 확인.

### L4. 세션 carry-over 점검
- `session["last_target"]`가 죽은 코드(쓰기 없음). dev target 잔여 miss 3건(a443f654, d6a5e982, fe98eb6a)이 세션 문맥 의존인지 확인.

## 동결 (재시도 금지 — attempts 참조)
- ask mode 3분 (값-수준까지 판별자 없음 확정) · 클래스 잔여 1(0937, age_hint 분산 확인) · mixed_local_external_candidates (strict 종속) · **E5/E5X (컴플라이언스 보류, 코드 제출 전 토글 제거)** · E6 (기각: 광의 규칙 확증, -0.0132)

## 검증된 전략 원칙
1. 개념 수준 일반화 2. **값-수준 재마이닝** (타입-수준 신호부재 판정을 두 번 번복: precondition_changed 콤보, R1~R6) 3. 중단-원천 원리 4. bake-off+래칫 5. 제출=단일변수 실험 6. 텔레메트리로 슬롯 우선순위 결정
