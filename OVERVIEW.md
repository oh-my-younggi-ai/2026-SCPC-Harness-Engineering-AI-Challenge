# SCPC 2026 AI 챌린지 — 프로젝트 정리 (성능 개선 기준 문서)

> 이 문서는 대회의 목표·규칙·데이터·채점 방식을 한 곳에 정리하고, **어디를 개선하면 점수가 오르는지**를 우선순위와 함께 담은 기준 문서입니다. 이후 성능 개선 작업(skill 포함)은 이 문서를 기준으로 진행합니다.

---

## 1. 한 줄 요약

주어진 **task JSON**(개인기기 AI 에이전트가 받는 요청 상황)을 읽고, **정해진 형식의 판단 결과 JSON**을 내놓는 **AI Agent Harness(파이썬 로직)**를 설계·구현한다. 이 harness를 700개 과제에 돌려 만든 `submission.csv`를 DACON에 제출하면, 서버가 보관한 정답과 비교해 점수를 매긴다.

**핵심은 "정답 하나를 맞히는 것"이 아니라, 같은 데이터·같은 제출 형식 안에서 task 상태·세션 이력·정책/안전 신호를 얼마나 일관되게 해석하는 "판단 로직"을 잘 설계했는가**이다. GPU·외부 대형 모델을 쓰는 대회가 **아니다**(외부 API 금지).

---

## 2. 대회 개요

- **주최**: 삼성전자 / **주관**: 삼성리서치 / **운영**: 데이콘(DACON)
- **형식**: 개인전(1인). 1차 예선 → 2차 예선 → 본선
  - **1차 예선**: Private 리더보드 상위 **40명** → 2차 예선 진출
  - **2차 예선**: 상위 **20명** → 본선 진출
  - **본선**: 오프라인. 솔루션 PT + 예선 문제 해결 과정 Q&A (발표자료 15페이지 이내)
- **예선 주제**: "AI Agent Harness 설계를 통한 창의적 문제 해결"
- 상위권은 예선 후 재현성 검증을 위해 **`harness.py` 실행 가능본 + README** 제출을 요구받을 수 있고, **비공개 task stream**으로 일반화 성능이 재검증된다.

---

## 3. 목표 / 최종 결과물 (Goal)

| 구분 | 내용 |
| --- | --- |
| **만들 것** | `FinalHarness.answer_task(task, session)` 형태의 파이썬 harness. task 하나를 받아 answer JSON 하나를 반환 |
| **제출물(예선)** | `submission.csv` — 700개 screening 과제에 대한 answer 전체를 담은 CSV |
| **제출물(상위권 검증)** | 같은 로직의 `harness.py` 실행본 + README (재현성/일반화 검증용) |
| **제출물(본선)** | 솔루션 발표자료(PPT, ≤15p) + 코드 |
| **성공 기준** | ① 공개 screening 700개에 대한 overall 점수 최대화 ② 동일 harness가 **처음 보는 task에도 작동**(일반화) |

> ⚠️ 공개 점수만 올리는 것이 전부가 아니다. 상위권 검증에서 **비공개 과제에도 잘 작동해야** 하므로, 특정 예시에 과적합(하드코딩·lookup table)하면 안 된다.

---

## 4. 데이터셋 — 무엇이 있고 무엇을 원하는가

모든 파일은 `data/`에 있다.

| 파일 | 정체 | 용도 |
| --- | --- | --- |
| `SCPC2026_Final_baseline.ipynb` | **모든 것의 기준 노트북** | 데이터 로드 → SLM facade → `FinalHarness` → 로컬 채점 → `submission.csv` 생성 전 과정. **여기서 시작** |
| `dev_tasks.jsonl` | 공개 dev task **120개** (JSONL, 한 줄=한 task) | 구조 이해·형식 연습·로컬 테스트 |
| `dev_answers.json` | dev 120개에 대한 **참조 정답** | 로컬 채점기 동작 확인용. **제출에 절대 포함 금지, 정답 외워서 쓰기 금지** |
| `screening_tasks.jsonl` | 공개 screening task **700개** (정답 없음) | **실제 리더보드 채점 대상** |
| `submission_schema.json` | 제출 JSON이 만족해야 할 스키마 | 형식 검증 |
| `sample_submission.csv` | CSV 제출 형태 예시 (BOM+UTF-8, 컬럼 1개 `submission`, 데이터 1행) | 형식 참조 |
| `TERMS_GUIDE.md` | **모든 필드·enum 용어집** | harness 로직 짜기 전 필독 |
| `SCPC2026_Final_data.zip` | 위 데이터 압축본 | 노트북이 자동 해제 |

**"무슨 결과를 원하나?"** → 각 task의 요청 맥락을 읽고, 아래 answer 필드(focal_id, target, control, content_scope, policy, plan_events 등)를 **서버 보관 정답과 최대한 일치**하게 채우는 것.

---

## 5. 입력(task) 구조

하나의 task = 개인기기/업무보조 에이전트가 받는 요청 하나를 단순화한 것. 주요 최상위 필드:

| 필드 | 의미 |
| --- | --- |
| `id` | task 고유 ID. 제출 답안 key와 매칭 |
| `session_id` | 같은 흐름(세션)에 속한 task 묶음 식별자 |
| `turn_index` | 세션 안에서의 순서 |
| `prompt` | 현재 사용자 요청 문장 |
| `visible_history` | 이전 turn 요약 이력 (`turn`, `summary`) |
| `device_state.objects` | 처리 후보 객체들 (message, calendar_event, file, gallery_item, payment_request, health_record, device_setting, iot_routine, personal_note 등). 각 `id`/`type`/`attrs` |
| `device_state.records` | 해석 보조 정보 (아래 표) |
| `personal_memory` | 사용자 장기 메모리 후보 (`user_preference` 등) |
| `available_actions` | plan에 쓸 수 있는 동작 이름 목록 |

**배열 순서는 우선순위가 아니다.** 세션 순서는 `turn_index`, history는 항목의 `turn` 값으로 판단.

**중요 record type** (판단의 핵심 신호):

- 안전/정책: `security_alert`, `consent`(granted/revoked), `privacy_guard`, `safety_mode`, `payment_policy`, `health_share_policy`, `external_share_policy`, `enterprise_policy_recall`
- 대상/모호성: `resolved_target`, `ambiguous_target`, `ambiguous_focal`, `target_changed_after_turn`, `amount_changed`, `merchant_verification`
- 메모리: `persistent_memory_write/recall`, `ops_memory_recall`, `memory_conflict`
- 간접 참조(중요): `focal_marker_refs`(marker→ref_code 매핑), `focal_resolution_trace`(어떤 marker를 따라갈지). 이력이 `WM-1234` 대신 `marker_alpha` 같은 marker 이름으로 후보를 가리킬 때, 매핑을 풀어 실제 object `id`를 `focal_id`로 사용해야 한다.

> record 이름(라벨) 하나만으로 답을 정하지 말고, 그 안의 `value`와 전체 task 맥락을 함께 봐야 한다.

---

## 6. 출력(answer) 구조

```json
{
  "focal_id": "obj_...",          // 이번 task에서 중심적으로 처리할 object의 id
  "target": "target_...",         // 최종 동작의 수신처/채널/앱/장치/메모리 저장소
  "control": "proceed|amend|hold|ask",
  "content_scope": {
    "mode": "raw|summary|redacted|status_only|none",
    "allowed_fields": [], "excluded_fields": [],
    "requires_user_confirmation": false
  },
  "policy": { "risk_flags": [], "violations": [], "requires_confirmation": false },
  "plan_events": [ {"verb": "read", "target": "obj_...", "args": {"purpose": "..."}} ],
  "user_response": "사용자에게 보여줄 짧은 응답",
  "audit_tags": [],
  "counterfactual": "판단이 달라질 조건 (점수 미반영)"
}
```

- **control**: `proceed`(진행) / `amend`(범위 축소·일부 수정 후 진행) / `hold`(보류·중단) / `ask`(사용자 확인 필요)
- **content_scope.mode**: 정보 사용 범위. `raw`/`summary`/`redacted`/`status_only`/`none`
- **plan_events**: 실제 실행 로그가 아니라 **처리 계획**. `verb`/`target`/`args` 필수, **최대 18개**. 동작 이름·대상·안전확인/실행의 상대 순서가 채점됨.
  - verb 목록: `read, verify, redact, summarize, dispatch, guard, clarify, update, schedule, toggle, pay`
  - **순서 규칙 예**: 동의 철회·보안 알림이 있으면 `dispatch`보다 `guard`가 앞서야 한다. 다단계는 `read→verify→redact→summarize→dispatch` 식으로 최신 record에 맞춰 구성.
  - `args`는 `TERMS_GUIDE.md`의 **공개 ontology**(권장 key: purpose, reason, scope, state, remove, mode, status, check, condition 등 / 정해진 value bucket)로 정규화되어 일부 반영. **임의 라벨 남발 금지** — 순서·target을 먼저 맞추고 args는 꼭 필요한 근거만.

---

## 7. 채점 방식 — 개선 우선순위를 결정하는 가장 중요한 부분

로컬 채점기(`score_dev_submission`, 노트북 셀 11)가 서버 채점 축·가중치를 근사한다. **채점은 계층적(gated)** 이라는 점이 핵심이다.

### 7.1 게이팅 구조 (반드시 이해)

```
focal_id 틀림  →  target = 0, control = 0  (focal이 하드 게이트)
target 또는 control 틀림  →  content_scope = policy = plan = 0
                            (dependent = target × control 로 곱해짐)
```

즉 **focal_id → (target, control) 순서로 맞히지 못하면, 나머지 축은 아무리 잘 채워도 0점**이다.

### 7.2 축별 가중치 (WEIGHTS)

| 축 | 가중치 | 채점 방식 |
| --- | --- | --- |
| focal | **0.18** | focal_id 정확 일치 (게이트) |
| control | **0.18** | 정확 일치 (focal 통과 시) |
| plan | **0.18** | 순서+비순서 recall 혼합, 초과 이벤트 감점 |
| content_scope | 0.17 | mode 일치(0.40)+allowed F1(0.25)+excluded F1(0.25)+confirm(0.10) |
| policy | 0.13 | risk_flags F1(0.45)+violations F1(0.35)+confirm(0.20) |
| target | 0.12 | 정확 일치 (focal 통과 시) |
| semantic_response | 0.04 | 로컬은 0 처리(서버만 반영) |
| counterfactual | 0.0 | 미반영 |

- 집합형 필드(`allowed_fields`, `excluded_fields`, `risk_flags`, `violations`)는 **F1** 로 채점 → 정밀도/재현율 균형 중요(과다 나열 금지).
- 모드·불리언은 **정확 일치**.
- plan 참조 정답은 `dev_answers.json`의 `expected_events`에 있음(내 answer의 `plan_events`와 비교).

### 7.3 개선 우선순위 (이 순서로 작업)

1. **focal_id 해석 강화** — 가장 높은 레버리지. marker/route 간접 참조, ambiguous_focal, target_changed 처리 정확도. focal이 틀리면 그 task는 사실상 전멸.
2. **control 판단** — proceed/amend/hold/ask 결정 로직. 안전·동의·정책 신호 반영.
3. **target 해석** — resolved_target, target_changed, ambiguous_target, latest_target_precedence.
4. 위 3개가 안정된 뒤에야 **content_scope / policy / plan** 품질이 점수로 실현된다.

> ⚠️ 로컬 채점기는 보수적(semantic_response·일부 서버 부분점수 미반영)이라 **실제 리더보드 점수는 로컬보다 다소 높게** 나올 수 있다. 로컬 점수는 절대값보다 **개선 방향의 지표**로 사용.

---

## 8. 실행 파이프라인 (아키텍처)

`FinalHarness.answer_task(task, session)` 하나가 answer dict 하나를 반환. 러너(`run_harness`)가:

1. task를 **`(session_id, turn_index, id)` 순으로 정렬**해 실행.
2. `session_id`별 dict를 turn마다 이어서 전달 → **세션 메모리**. 이전 turn에서 얻은 정보(해석된 target, 동의 상태, 메모리 write 등)는 여기 저장해야 다음 turn이 활용.
3. harness가 보기 전 `participant_task_view`가 `expected_*`/`*_rubric`/`answer` 등 채점 필드를 제거 → **런타임에 정답 필드 의존 금지**.

권장 내부 분해(baseline도 이 구조): `choose_focal → infer_target → decide_control → build_content_scope → build_policy → build_plan_events → update_session_memory`.

### FixedSLMClient facade

`slm.summarize_task(task)`는 **고정된 로컬 키워드 기반 evidence 추출기**(risk flag, redaction/confirmation 힌트, audit tag). **정답을 알려주는 장치가 아니다** — focal/target/control 등을 직접 정해주지 않는다. 보조 신호일 뿐이며 반드시 로컬이어야 한다.

---

## 9. 규칙 / 실격 요소 (반드시 준수)

- **외부 LLM API·네트워크 호출·임의 외부 모델 금지.** 제공된 `FixedSLMClient`만. 제출 `meta`는 반드시:
  - `fixed_slm_policy: "local_fixed_slm_only"`, `uses_external_api: false`, `model_id: "scpc-final-fixed-slm-local-facade"`
  - 권장 `temperature: 0.0`, `seed: 42` *(주의: baseline 노트북 러너는 `seed: 2026`으로 되어 있음 — 규칙 권장값은 42)*
- **하드코딩 금지.** 특정 `task_id`/`session_id`에 정답 직접 입력, 공개 예시 문장·record 값 암기, 공개셋 전용 lookup table 금지. **처음 보는 task에 일반화**되어야 함.
- **데이터 leakage 금지.** 평가셋 정답 분포 분석·수작업 라벨링 금지.
- **개발 단계 AI 코딩 도구 사용은 허용**되나, 최종 답안 생성은 제공 데이터+fixed SLM 기준을 따라야 함.
- **제출**: `submission.csv`, UTF-8, 컬럼 `submission` 1개, 데이터 **1행**, 그 단일 셀에 answer JSON 전체(`submission_schema.json` 최상위 구조). JSON 파일 직접 제출 불가. **1일 최대 5회**.
- screening payload는 **700개 id 정확히**(누락·초과 없이) 포함해야 함.

---

## 10. 제출 형식 상세

```
submission
"{""schema"":""scpc.final.answer.v1"",""meta"":{...},""answers"":{""task_..."":{...}}}"
```

- 각 answer 필수 필드: `focal_id, target, control, content_scope, policy, plan_events`
- `control` ∈ {proceed, amend, hold, ask}
- `content_scope.mode` ∈ {raw, summary, redacted, status_only, none}
- `plan_events` ≤ 18, 각 항목 `verb`/`target`/`args`

---

## 11. 지금 상태 & 다음 할 일

- **현재**: baseline 노트북(약한 출발점)만 존재. `FinalHarness`의 판단 로직을 직접 개선해야 점수가 오른다.
- **작업 방식(권장 루프)**:
  1. `SCPC2026_Final_baseline.ipynb` 셀 7의 `FinalHarness` 로직 수정
  2. 셀 위→아래 실행, 셀 13에서 `score_dev_submission`으로 dev 120개 로컬 채점
  3. **축별 점수(axes)** 를 보고 병목 축 파악 → §7.3 우선순위대로 개선
  4. 마지막 셀로 700개 `submission.csv` 생성 → DACON 제출(1일 5회 한도)
  5. 상위권 대비: 로직을 `harness.py`로 깔끔히 추출 가능하게 유지(노트북 전용 상태 배제)
- **개선 아이디어 출발점**: focal marker/route 해석 정교화, control 결정 규칙(안전>동의>정책 우선순위), target 최신성(latest_target_precedence), plan 이벤트 순서(guard 우선), scope/policy 집합의 F1 균형.

---

## 12. 참고 파일 빠른 링크

- 용어·필드 상세: `data/TERMS_GUIDE.md`
- 규칙 원문: `public_rules/rules.md`, `public_rules/scoring.md`, `public_rules/introduction.md`
- 스키마: `data/submission_schema.json`
- 코드·채점기: `data/SCPC2026_Final_baseline.ipynb` (셀 5 SLM, 셀 7 harness, 셀 9 runner, 셀 11 채점기, 셀 16 제출 생성)
- Claude용 요약: `CLAUDE.md`
