# SCPC Harness 개선 로그

> 매 반복: 가설 → 변경 → 점수 변화(before→after) → 결정. 채점 게이팅: focal 틀리면 target·control=0, target·control 틀리면 scope·policy·plan=0 (OVERVIEW §7).

| 지표 | 값 |
| --- | --- |
| 현재 overall (전체) | **0.8010** (dev) |
| **리더보드 실측** | **0.58299** (Iter 010 제출, transfer 수리 검증됨) |
| CV 일반화 평균±표준편차 | 0.6498 ± 0.0324 (k=5) |
| focal 정확도 | **100%** (120/120) |
| 활성 규칙 수 (풀 크기) | 5 (+ask_target) |
| ratchet high-water (CV) | 0.7971 |
| 누적 반복 수 | 4 (2 KEEP, 2 REJECT) |
| 최고 기록 (dev CV) | 0.3419 |
| **실제 리더보드 (screening 700)** | **0.3295** (CV 0.342±0.02 추정과 일치 → 과적합 없음·transfer 확인) |
| **본선 컷** | **0.89** (현재 대비 대격차 — 결정론적 reference 로직을 축별로 해독해야) |

**노이즈 관측(중요):** CV fold 표준편차 = **0.0358** (per-fold 0.043~0.136, 3배 스프레드). 즉 CV 기준 **~0.036 미만의 개선은 노이즈와 구분 불가**. 초기 focal 대형 개선은 이보다 크므로 감지 가능하지만, 미세 튜닝은 못 믿는다. → 포트폴리오 층(ablation/composition)은 이 노이즈 위에서 무의미하므로 **DEFERRED 유지**가 데이터로 확인됨.

---

## Iter 000 — 2026-07-07 — BASELINE

**변경 내용:** 주최 노트북(`SCPC2026_Final_baseline.ipynb`) 셀 1/3/5/7/9/11/16을 `harness/`로 verbatim 추출. `scpc_core.py`(고정 framework) + `harness.py`(FinalHarness, 개선 대상) + `run_local.py`(CV 오케스트레이터). 로직 변경 없음.

**재현성 검증:** 원본 노트북 셀13 실행 결과 = `overall 0.0882, focal 0.2917` → 추출본과 **정확히 일치**. (seed 2026→42는 meta 표기만, 결정적 출력에 무영향)

**점수(baseline):**

| 축 | 값 | 가중치 |
| --- | --- | --- |
| overall (전체) | 0.0882 | — |
| CV 일반화 평균 | 0.0880 ± 0.0358 | — |
| focal | 0.2917 | 0.18 |
| target | 0.1167 | 0.12 |
| control | 0.0833 | 0.18 |
| content_scope | 0.0196 | 0.17 |
| policy | 0.0087 | 0.13 |
| plan | 0.0126 | 0.18 |

**진단(데이터 관찰):** 전 축이 focal(29.2%) 게이트에 막혀 downstream이 near-zero. **focal 실패 85개 중 72개(85%)가 `marker_indirect`** — `focal_marker_refs`(marker→ref_code 매핑) + `focal_resolution_trace`로 후보를 간접 지시하는데 baseline `choose_focal`이 이를 처리하지 않음(직접 id / ref_code / 토큰겹침만 봄). TERMS_GUIDE §focal_marker_refs에 문서화된 메커니즘.

**다음 후보 (Iter 001):** `choose_focal`에 marker/route 해석 추가 → `marker_to_ref`로 marker를 object ref_code에 매핑, `focal_resolution_trace`로 따라갈 marker 선택 → 해당 object id를 focal로. **일반화 규칙**(특정 task_id 아님). 기대: focal ~29%→대폭 상승 + downstream 게이트 해제로 overall 노이즈플로어(0.036) 초과 상승 예상. 대상 메서드: `choose_focal`.

---

## Iter 001 — 2026-07-07 — KEEP

**catalog 항목:** `focal_marker_refs`  ·  **지문:** `choose_focal:focal_marker_refs:marker_route_resolution`

**가설:** marker 간접참조 미처리로 focal 실패 72/85. `choose_focal`에 marker→ref→object 해석을 추가하면 focal 대폭 회복 + downstream 게이트 해제.

**변경 내용:** `harness.py` `choose_focal` — 맨 앞에 `_resolve_marker_focal` 최우선 적용. 경로: `focal_resolution_trace.latest_phase` → `phase_to_marker[phase]` → marker → `focal_marker_refs.marker_to_ref[marker]` → ref_code → `attrs.ref_code` 일치 object. 일반화 규칙(하드코딩 없음). 사전 검증: dev marker task **83/83(100%)** 정확 해석. 단위테스트 `tests/test_marker_focal.py`(합성 입력) 추가·통과.

**점수 변화:**

| 축 | before | after | Δ |
| --- | --- | --- | --- |
| overall (전체) | 0.0882 | 0.2911 | **+0.2029** |
| CV 일반화 평균 | 0.0880 | 0.2894 | **+0.2014** (노이즈 0.036의 5.6배) |
| focal | 0.2917 | 0.8917 | +0.60 |
| target | 0.1167 | 0.3917 | +0.275 |
| control | 0.0833 | 0.2750 | +0.192 |
| content_scope | 0.0196 | 0.0697 | +0.050 |
| policy | 0.0087 | 0.0617 | +0.053 |
| plan | 0.0126 | 0.0792 | +0.066 |

**task 영향:** 고침 +72 / 깨짐 −0 (순 +72)

**회귀 / 테스트:** 축적 단위테스트 green · 래칫 통과(CV 0.088→0.289) · 회귀 task 없음

**coverage:** focal marker 신호 handled

**결정:** KEEP — CV 델타 +0.201이 노이즈 플로어(0.036)를 압도. 게이팅 캐스케이드 실증(focal 하나로 전 축 상승).

**다음 후보 (Iter 002):** `decide_control` 과다-"ask" 교정. focal-correct 107개 중 control 오답의 대부분이 정답이 ask가 아닌데 ask로 예측(proceed→ask 31, amend→ask 19, hold→ask 9 = 59). `requires_confirmation`/ambiguous_* 트리거가 너무 광범위. 병행: `infer_target` memory_store/route 해석(target 오답 다수). 대상: `decide_control`, `infer_target`.

---

## Iter 002 — 2026-07-07 — KEEP

**catalog 항목:** `control_ask`  ·  **지문:** `decide_control:ask_triggers:drop_ambiguous_and_reqconf_add_target_changed`

**가설:** control 과다-ask(59). `ambiguous_target`/`ambiguous_focal` 라벨과 SLM `requires_confirmation`이 판별력 없이 ask를 남발. 이들을 트리거에서 제거.

**진단 근거(데이터):** false-ask 59개 중 93%가 resolved_target/trace 보유(모호성 해소됨). 그러나 resolved 신호는 true-ask에도 92% 존재 → 판별 불가. 결정적으로 **동일한 `ambiguous_target` 값(`approved_channel_or_visible_recipient` 등)이 true-ask와 false-ask 양쪽에 동일 출현** → 이 라벨은 ask 판별 신호가 아님. 공짜 채점으로 5개 트리거 조합 실험 → 후보 A(ambiguous_* + reqconf 제거, target_changed 추가)가 CV 최고·분산 최저.

**변경 내용:** `harness.py` `decide_control` — ask 트리거를 `{amount_changed, merchant_verification, duration_ambiguous, memory_conflict, target_changed_after_turn}`로 축소(ambiguous_target/ambiguous_focal/routine_scope, requires_confirmation 제거). 단위테스트 `tests/test_control_ask.py` 추가·통과.

**점수 변화:**

| 축 | before | after | Δ |
| --- | --- | --- | --- |
| overall (전체) | 0.2911 | 0.3419 | **+0.0508** |
| CV 일반화 평균 | 0.2894 | 0.3419 | **+0.0525** (노이즈 0.034의 1.5배) |
| CV 분산(±) | 0.0341 | 0.0215 | 감소(더 안정) |
| control | 0.2750 | 0.4000 | +0.125 |
| content_scope | 0.0697 | 0.1342 | +0.065 |
| policy | 0.0617 | 0.1185 | +0.057 |
| plan | 0.0792 | 0.1345 | +0.055 |

**task 영향:** 고침 +32 / 깨짐 −17 (순 +15)

**회귀 / 테스트:** 축적 단위테스트 green(marker+control) · 래칫 통과(CV 0.289→0.342) · **회귀 17개 = 진짜 ask인데 ambiguous_* 라벨에만 의존하던 task**(라벨 값이 false-ask와 동일해 현 신호로는 분리 불가). 알려진 비용으로 수용, 백로그 이월.

**결정:** KEEP — CV +0.053(노이즈 초과)·분산 감소·순 +15. downstream 3축 동반 상승. 다만 17 회귀는 미해결 신호 문제.

**다음 후보 (Iter 003):** `infer_target` — target 0.392가 다음 게이트. focal-correct 107개 중 target 오답 상위: `memory_store`를 project_room/privacy_review 등으로 오예측(25+). `infer_target`이 memory_store를 `persistent_memory_write`에만 의존. memory/route target 신호 확장 필요. + (백로그) true-ask 17개 정밀 분리 신호 탐색.

---

## Iter 003 — 2026-07-07 — REJECT (변경 없음)

**catalog 항목:** `target_memory_store`  ·  **지문:** `infer_target:memory_store:personal_note_or_prompt_keyword`

**가설:** target 오답 최대 클러스터(memory_store 30개)를 focal type=personal_note / prompt 키워드(저장·메모리·기기 내부)로 잡으면 target↑.

**진단(데이터):** memory_store는 record type으로 안 갈림(current_request_hint 등이 양쪽 공통). 신호는 prompt 의미 + personal_note focal(10/10). **둘 다 dev 편중**(personal_note dev 17.5% vs screening 4.9%; 키워드 dev 38% vs screening 26%).

**실측(공짜 채점, 후보 4개):**

| 후보 | overall | CV±σ | 판정 |
| --- | --- | --- | --- |
| baseline | 0.3419 | 0.3419±0.021 | — |
| C1 personal_note→ms | 0.3404 | 0.3417±0.034 | overall↓, σ↑ |
| C2 prompt키워드→ms | 0.3371 | 0.3375±0.033 | ↓ |
| C3 둘다 | 0.3285 | 0.3305±0.046 | 더 나쁨 |

**결정:** REJECT — 모든 후보가 overall 하락 + 분산 증가. target 축은 오르나 overall이 떨어짐(다른 축 파손). 신호도 dev 편중이라 screening transfer 없음. 코드 변경 없이 baseline 유지. **attempts에 기록해 재시도 차단.**

**교훈:** 쉬운 지배-신호 win(marker, control-noise)은 소진됨. target/scope/policy는 깔끔한 기계적 규칙이 없는 다신호 판단 — 새 판별 신호(surface recipient vs resolved_target 불일치 등)를 찾아야 다음 진짜 win이 나온다. 무료 채점 덕에 dev만 고치는 함정을 코드 커밋 전에 걸러냄.

**다음 후보:** 백로그 #2(진짜 ask 신호 — screening ambiguous_target 41%라 중요) 또는 여기서 매듭짓고 submission 확정.

---

## Iter 003~007 — control 리버스 엔지니어링 종합 (전부 REJECT, 코드 변경 없음)

리더보드 0.3295 확인 후, 본선 컷 0.89를 위해 control(다음 게이트)을 집중 해독 시도. **결론: control은 일반화 가능한 규칙으로 안 뚫림.** 소진한 접근:

| 접근 | 결과 |
| --- | --- |
| 단일 record → control | ≤50% 순도 |
| record 2~3개 / **full phase 조합** | 33~50% (동일 routing 상태가 4개 control 전부로 갈림) |
| prompt 단일 토큰 / 키워드 사다리 | 44%→31% 악화 |
| prompt 템플릿 lookup | dev↔screening 겹침 0 → 불가·과적합 |
| **held-out 특징 마이닝 (순수 Python)** | 46±10% = 현행과 동일 (100% 순도 dev 신호는 과적합 아티팩트) |
| phase 메커니즘 (`latest_phase_rule`, route_binding_order) | 비결정론 |
| **prompt "단," 제약절 phrase 사다리** | 45.8% (현행 44.2%와 노이즈 내), 제약절 있는 task 52/120뿐 |

**핵심 발견**: control 신호는 records/phase가 아니라 **prompt의 "단," 제약절 자연어 의미**에 있음(예: "실행하면 안 된다"→hold, "다시 확인하라는 지시"→ask). focal의 marker처럼 깔끔한 결정론 경로가 아니라 **정밀 NL 이해가 필요**하고, 고정 crude SLM + 규칙으로는 일반화 정확도를 못 냄. **모든 실패를 attempts에 기록해 재시도 차단.**

**정직한 상태**: 이 harness 접근의 천장 ≈ control 44%, overall ~0.33. 0.89는 우리가 이번에 찾지 못한 결정론 키 또는 정밀 NL 파싱이 필요. baseline+focal marker(검증된 win)가 견고한 토대이자 정직한 도달점.

---

## Iter 008 — 2026-07-07 — DIAGNOSIS: 생성기 클래스 구조 해독 (0.89로 가는 결정적 경로 발견)

**질문**: 0.89를 뚫으려면 결정적으로 무엇이 필요한가?

**게이트 수학**: 0.89 = focal ~97% + target·control 각 ~95% + 하위품질 ~90% 필요. 현재 target 39%/control 40%, dependent 게이트 통과 21%. **우회 불가 — target×control이 유일한 길.**

**결정적 발견 (①→②→③ 연쇄)**:
1. **`expected_events` args = 생성기 내부 "이유" 라벨이며 → control 100% 결정론** (n≥3 전부): `local_update`→proceed, `minimal_disclosure`/`redacted`→amend, `precondition_invalidated`→hold, `route_resolution_required`/`clarify_precondition`→ask.
2. **이유 클래스가 answer 전체 골격을 결정**: control 100% + scope.mode 60~100% + plan verb열 100% + target 종류 50~95%. 즉 **task는 ~6개 시나리오 클래스에서 생성되고, 클래스가 정답 템플릿을 정한다.** 이게 0.89가 가능한 이유.
3. **클래스 판별 신호는 prompt 절 구문 패밀리**("내부 업데이트로 끝내라/상태값만 갱신"=local_update, "깨졌으므로 멈춰야"=invalidated, "확정되지 않았으므로 먼저 확인"=confirm)이며 **screening에도 실재** (local_update 계열 136/700, redact 169/700, confirm 62/700, invalidated 37/700). Opus 세션의 마이닝 실패 원인 = 단일 토큰 단위로 봐서 구문 패밀리를 못 잡음.

**결정적 계획 (0.89 경로)**:
- **Phase 1 — 클래스 분류기**: dev 120 전 클래스의 절 표현을 구문 패밀리로 정리(순수 Python) + records 보조 신호(authority_incomplete 등) 결합 → held-out 클래스 정확도 측정. 클래스 정확도 ≈ control 정확도.
- **Phase 2 — 클래스별 answer 템플릿**: 클래스 → (control, scope.mode, plan verb열+args, target 규칙) 방출. focal/route 구체값은 기존 marker 해석 재사용.
- **Phase 3 — 클래스 내 세부**: allowed/excluded fields, plan args, policy flags를 클래스별 일반 규칙로.
- 예상: 클래스 정확도 90% 달성 시 overall ~0.75+ (target 세부, policy F1이 잔여 갭).

---

## Iter 009 — 2026-07-07 — KEEP (클래스 디코더 + 템플릿: 0.342 → 0.650)

**catalog 항목:** `generator_class`  ·  **지문:** `answer_task:scenario_class_decoder:clause_families_plus_records_plus_templates`

**구현 (Phase 1+2):**
- `classify_task`: "단," 절 구문 패밀리(최우선: local/invalid/confirm/redact 4계열) → 절 없으면 record 신호(안전/consent→hold, persistent_memory_write→local, target_changed·memory_conflict 등→ask, user_binding_pending+dispatch_blocked→hold, authority_incomplete→ask, external_share_policy·strict→minimal). **클래스→control 정확도 86.7%** (현행 44.2%).
- 클래스별 answer 템플릿: dev에서 클래스별 결정론 확인 후 방출 — scope(allowed/excluded/ruc), policy(flags 조합식+violations), plan verb열+args (local: read/verify/update 40/40 동일, invalid: read/guard 20/20 등). target 규칙: local→memory_store, ask→user, 그 외→resolved_target→recipient.
- 핵심 방법론 교정: **이전 record 순도 분석이 실패한 건 절 있는 task가 섞여서** — 절이 record를 override하므로 절 없는 부분집합에서 record 매핑이 순수해짐(persistent_memory_write→local 100%, target_changed→ask 100%, safety/consent→hold 100%).

**점수 변화:**

| 축 | before | after | Δ |
| --- | --- | --- | --- |
| overall (전체) | 0.3419 | **0.6496** | **+0.3077** |
| CV 일반화 평균 | 0.3419 | 0.6498 | +0.3079 (노이즈의 ~10배) |
| target | 0.3917 | 0.6833 | +0.29 |
| control | 0.4000 | 0.7583 | +0.36 |
| content_scope | 0.1342 | 0.5563 | +0.42 |
| policy | 0.1185 | 0.5404 | +0.42 |
| plan | 0.1345 | 0.5878 | +0.45 |

**task 영향:** 고침 +80 / 깨짐 −9 (순 +71) · 테스트 3종 green (`test_class_decoder.py` 추가) · 래칫 0.342→0.650

**다음 병목:** ① focal 89.2%가 이제 하드캡(13개 miss — marker 없는 다후보 task) ② 클래스 오분류 잔여 16개(internal_binding 계열 애매) ③ ask의 target(user 42%뿐) ④ scope/policy 세부 F1. 상위권 0.89까지 잔여 갭 ~0.24.

---

## Iter 010 — 2026-07-07 — KEEP (transfer 수리: 절 개념 계열화)

**리더보드 실측 (Iter 009 제출):** dev 0.650인데 **실측 0.3442** — 심각한 transfer 실패. 원인 진단:
- submission 파일은 정상(새 harness 지문 확인). 문제는 **절 매칭**: screening은 62%가 "단," 절을 갖는데 dev-문자 그대로인 패밀리가 **432개 중 417개(96.5%)를 미매칭** → 70%가 fallback(amend)으로 쏠림 (local_update는 4/700).
- 미매칭 절을 집계하니 **고유 23종**뿐, 전부 기존 4개 의미 계열의 paraphrase ("외부 전송 하지 말고 장치 내부 상태 표시만 갱신"=local 등).

**변경:** `CLAUSE_*` 패밀리를 dev-문자에서 **개념 어휘(같은 지시의 표현 계열)**로 확장. 결과:
- screening 절 매칭 15/432 → **432/432 (미매칭 0)**
- screening 클래스 분포 정상화: local 0.6%→22%, amend 70%→35%, invalid 16%, ask 23% (dev 33/23/16/21%와 근사)
- **dev 정확도 불변** (클래스 86.7%, overall 0.6496, CV 0.6498) — 개념 확장이 dev에서 오발화 없음. 테스트 3종 green.

**교훈(중요):** dev에서 도출한 규칙은 **문자 수준이 아니라 개념 수준**으로 일반화해야 transfer된다. dev 점수는 이 수리를 못 본다(원래 dev는 다 맞던 부분) — **검증은 리더보드 제출만 가능.**

**제출 예산:** 주최측이 1일 한도를 5→**3회**로 변경.

**리더보드 실측 (3차 제출): 0.58299** — 0.3442에서 +0.24. 개념 계열화 수리가 검증됨. dev 0.650과의 잔여 갭 ~0.067은 screening 세부 변형(절 없는 task의 fallback, fields/args 표현차)으로 추정.

## 다음 세션 우선순위 (0.583 → 0.89 잔여 갭 ~0.31)

1. **focal 13개 miss** (marker 없는 다후보 task) — focal은 하드 게이트라 최우선. dev에서 miss 패턴 분석부터.
2. **클래스 혼동 잔여 16개** — internal_binding 계열 애매 케이스. 절 없는 task의 record fallback 정밀화.
3. **screening 전용 진단** — 절 없는 screening task(38%)의 분기 분포를 dev와 비교해 fallback 규칙 검증.
4. **ask의 target** (user 42%뿐) — clarify target이 user/TGT로 갈리는 조건 해독.
5. **scope/policy 세부 F1** — allowed/excluded fields, risk_flags 조합식 정밀화 (게이트 열린 뒤 효과 큼).
6. 검증 규율 유지: dev 정확도(라벨) + screening 분포(무라벨) + 리더보드(하루 3회) 3중 체크. **개념 수준 일반화 원칙** 준수.

---

## Iter 004 — 2026-07-07 — REJECT (변경 없음)

**catalog 항목:** `ask_precision`  ·  **지문:** `decide_control:ask_precision:surface_resolved_mismatch_or_relabel`

**가설:** Iter 002서 잃은 true-ask 17개를 새 신호로 복구(표면 recipient vs resolved_target 불일치 등).

**실측:** (1) 불일치 신호는 판별 실패(TP=2/FP=6). (2) 전 record type 전수 스캔: ask에 100% 집중되는 건 `target_changed_after_turn`뿐인데 **이미 Iter 002서 사용 중**. 나머지 최선이 ambiguous_focal 40%(6/15) — 순 음성. ask 기저율 22%(24/107)를 어떤 특징도 못 모음.

**결정:** REJECT — 사용 가능한 신호로 ask는 분리 불가. 코드 변경 없음. attempts 기록.

**결론(플래토 도달):** 깔끔한 지배-신호 win 2개(marker focal, control ask-noise) 소진. target·ask는 같은 표면 신호가 다른 정답으로 갈리는 다신호 판단이라 120-task·노이즈 0.02~0.03 환경에서 클린 룰이 안 나옴. 추가 이득은 (a) 더 정교한 다신호 모델링(120개서 과적합 위험) 또는 (b) 새 파생 특징 발굴 필요. **현 상태(0.342, transfer되는 win 2개)가 자연스러운 매듭.**

---

---

## Iter 011 — 2026-07-08 — KEEP (history 선택 서사 focal: 0.650 → 0.7365, focal 100%)

**지문:** `choose_focal:history_selection_narrative:designation_and_bound_ordinal`

**진단:** focal miss 13개 전부 marker-없는 다후보 task이며, visible_history 서사가 후보 WM 코드 중 하나를 지목("두 번째 후보만 확정" / "최종 승인 후보 WM-X" / "가운데 항목만" / "승인 표시가 남은 것은"). baseline은 vh에서 아무 ref_code나 첫 매칭을 집어 오답.

**구현:** `_resolve_history_focal` — 개념 그룹 2종: ① 지목형 정규식(고정/지정/통과/승인 유지/최종 승인/잔존) ② **선택 표지에 결합된 서수**(단독 서수 금지 — "첫 번째와 세 번째는 보류, 두 번째만 확정" 문장에서 배제 서수에 낚이지 않도록). marker 해석 다음, 기존 규칙 앞에 배치.

**transfer 사전 검증 (Iter 010 교훈 적용):** 첫 구현이 dev-문자에 붙어 screening 발화 0/700 → screening의 marker-없는 237개 task의 vh 서사를 집계하니 **6종 paraphrase**(같은 두 개념) → 개념 정규식으로 확장. 도중 dev 회귀 버그(서수 오결합, 0.737→0.687)를 잡아 선택-표지-결합 규칙으로 수정. 최종: **dev focal 100% + screening 발화 237/237 + 회귀 0.**

| 축 | before | after |
| --- | --- | --- |
| overall | 0.6496 | **0.7365** |
| CV | 0.6498±0.032 | 0.7335±0.043 |
| focal | 0.892 | **1.000** |
| target | 0.683 | 0.767 |
| control | 0.758 | 0.867 |
| scope/policy/plan | .56/.54/.59 | .64/.61/.67 |

테스트 4종 green(`test_history_focal.py` 추가) · 래칫 0.650→0.7335 · submission 재생성(오늘 3회 미사용).

**다음:** ① 클래스 혼동 잔여(control 86.7% → miss 16) ② target 0.767 (ask target user/named 갈림, minimal의 resolved 예외) ③ scope/policy fields F1 ④ plan args 세부.

---

## Iter 012 — 2026-07-08 — KEEP (ask target 소스 해독: 0.7365 → 0.7641)

**진단:** target miss 28 중 ask 클래스 12가 user 일괄 규칙에 깨짐. 정답 추적 결과 named target의 출처 3종: ① `target_changed_after_turn` 값이 새 대상 이름을 직접 담음 ② **cross-session 메모리 회수** — `persistent_memory_recall`의 memory_key로 이전 `persistent_memory_write` 프로필을 찾고, 도메인이 필드를 정함(승인/규정→approval_channel, 조명→dusk_room, 쿠폰→preferred_channel, 기본 health_channel). 검증: recall형 12개 중 9개의 정답이 저장 프로필 값에 존재 ③ resolved_target — 단 실측서 true-user를 깨뜨려 **기각**(공짜 채점 비교: with③ 0.7401 vs no③ 0.7641).

**결과:** target 0.767→0.817, overall 0.7365→**0.7641** (CV 0.7606), **+6/−0**, 테스트 4/4. self.memory(세션 메모리)를 처음으로 읽기 경로에 활용 — 대회가 강조한 session memory 차원 개통.

**잔여 병목:** 클래스 혼동 16(신호 없음 확인, 보류) · invalidated target user/named 갈림(11) · scope/policy fields F1 (.67/.66) · plan args (.72).

---

## Iter 013 — 2026-07-08 — KEEP (policy flags 정밀화: 0.7641 → 0.7676)

**리더보드 실측 (Iter 011+012 제출): 0.6837** (0.583→+0.10, transfer 확인. dev 갭 ~0.08 안정 패턴)

**변경:** `sensitive_content` 플래그를 SLM 키워드 대신 **focal.attrs.contains ∩ 민감필드**(amount→numeric_value 정규화)로 판단 — dev 검증 95%+ 정합. excluded_fields 후보 공식들(교집합 변형 3종)은 bake-off에서 전부 악화라 기각. policy 0.663→0.691, **+37/−0**, 테스트 4/4.

**잔여 병목(다음 세션):** scope excluded 21건(클래스별 혼합 규칙 미해독) · risk_flags 코어 변형(precondition_changed/target_ambiguity 부가 조건) · plan args 세부 · 클래스 혼동 16(신호 없음 확인, 보류) · invalidated target user/named(11).

---

## Iter 014 — 2026-07-08 — KEEP (클래스 템플릿 세부 3종: 0.7676 → 0.7718)

dev 검증된 결정론 규칙 3개 (bake-off로 채택, +22/−0):
1. minimal excluded_fields = focal.contains∩민감(정규화) 있으면 그것, 없으면 [raw_quote]
2. `ambiguous_target` record → `target_ambiguity` flag (P=1.00/R=0.93)
3. redact의 remove arg = sensitive_fields ⟺ focal 민감 보유 (**100% 결정론** 9/9·19/19). clarify target은 이미 user 26/26 정답.

기각: ask/local excluded 변형(악화), precondition_changed flag(단일 record 신호 없음).

**잔여:** scope .68/policy .70/plan .73 내 미해독 변형 · 클래스 혼동 16(보류) · invalidated target(11) · dev-LB 갭 0.08 (screening fallback 품질).

---

## Iter 015 — 2026-07-08 — KEEP (hold target의 중단-원천 규칙: 0.7718 → 0.8010)

**발견:** invalidated(hold)의 target user/named 갈림 = **중단의 원천**. 절(최신 지시)로 중단된 hold → target=user (6/6), record 신호로 중단된 hold → 원래 대상 유지·resolved/recipient (9/9). 의미적으로도 자연: 지시로 멈추면 사용자 보고, 신호로 멈추면 원 라우트 유지.

**결과:** target 0.817→0.867, overall **0.8010** (CV 0.7971), +6/−0, 테스트 4/4.

**현 축:** focal 1.00 · control .87 · target .87 · scope .70 · policy .73 · plan .77
