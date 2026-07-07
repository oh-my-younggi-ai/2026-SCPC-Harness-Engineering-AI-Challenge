---
---

# Step 0: Bootstrap — 인프라 구축 (최초 1회)

주최측 framework(노트북)를 **버리지 않고 그대로 들어내어** 루프가 편집·채점하기 좋은 형태로 만든다.

## RULES

- 출력 언어는 항상 `{communication_language}`.
- 노트북의 `FixedSLMClient`, `run_harness`, `score_dev_submission`, `write_submission_csv` 로직은 **한 글자도 바꾸지 말고 그대로 복사**한다. 채점·제출 형식은 주최측 기준이 정본이다.
- 새로 짜는 것은 오직 **오케스트레이션(run_local.py)** 과 **k-fold CV 분할·세그먼트/per-task 진단 출력**뿐이다.

## INSTRUCTIONS

### 1. 노트북에서 코드 추출

`{notebook}`의 셀을 읽어 아래 매핑대로 `{code_dir}/`에 모듈로 분리한다. **로직 변경 금지, 복사만.**

| 노트북 셀 | 대상 파일 | 내용 |
| --- | --- | --- |
| 셀 1 | `constants.py` | `SUBMISSION_SCHEMA`, `FIXED_SLM_ID` 등 상수 |
| 셀 3 | `io_utils.py` | `load_json`, `load_jsonl` |
| 셀 5 | `slm.py` | `FixedSLMClient` (고정 인프라) |
| 셀 7 | `harness.py` | 헬퍼(`records_of`, `objects_of`, `record_map`, `text_of`, `object_text`) + **`FinalHarness`** ← 개선 대상 |
| 셀 9 | `runner.py` | `participant_task_view`, `answer_one`, `run_harness` |
| 셀 11 | `scorer.py` | `validate_payload`, 채점 함수들, `score_dev_submission` |
| 셀 16 | `io_utils.py` | `write_submission_csv` 추가 |

import 관계를 맞춘다: `harness.py`는 `slm`, `io_utils`, `constants`에서 필요한 것을 import. `runner.py`는 `harness`, `constants`. `scorer.py`는 `constants`.

`harness.py` 상단에 주석으로 명시: **"이 파일이 상위권 재현성 검증용 harness.py 제출 산출물이며, FinalHarness만 개선 대상이다."**

**규칙 파이프라인 골격(점진적 전환의 씨앗):** `{rules_dir}/`(빈 `__init__.py` 포함)와 `{tests_dir}/`를 만든다. `FinalHarness`는 노트북 원본 로직을 그대로 두되, **활성 ruleset 설정(`{ruleset}`)을 읽어 켜진 규칙을 정해진 순서로 실행**하는 얇은 엔진 훅을 남긴다(각 규칙은 `id`로 식별, on/off·순서·파라미터 가능). 이래야 ⑤버전/⑦ablation/⑧composition이 성립한다. **이번 부트스트랩에서는 로직을 규칙으로 쪼개지 않는다** — 이후 개선이 건드리는 영역부터 하나씩 `{rules_dir}/<signal>.py`로 추출한다(step-03).

### 2. scorer.py에 per-task 진단 노출 (최소 확장)

`score_dev_submission`의 집계값(overall, axes 평균)은 **그대로 유지**하면서, 반환 dict에 `rows`(task별 `{task_id, score, axes}` 리스트)를 **추가**한다. 기존 계산은 건드리지 않고 이미 만드는 `rows`를 반환에 포함만 한다. 이래야 step-02 진단이 task 단위로 병목을 본다.

### 3. run_local.py 작성 (새 오케스트레이터)

`{code_dir}/run_local.py`를 만든다. 기능:

- `data/dev_tasks.jsonl`, `data/dev_answers.json` 로드.
- **k-fold CV 분할**: dev의 고유 `session_id`를 정렬 후 결정적으로 **5겹**으로 나눈다(정렬 인덱스 %5). 분할을 `{folds}`에 저장/재사용(재현성). 일반화 점수 = 각 fold를 held-out으로 채점한 overall의 평균.
- **활성 ruleset 로드**: `{ruleset}`(켜진 규칙 id·순서·파라미터)를 읽어 harness가 그 조합으로 동작하게 한다. `--ruleset <cfg>`로 임의 조합 override(ablation·composition 실험용).
- harness를 dev 전체에 실행 → `score_dev_submission`으로 채점.
- **세그먼트 분해**: 각 task를 domain(focal object type·주요 record type에서 추론: payment/health/privacy/message/calendar/iot/settings/memory)으로 분류. per (axis × domain × catalog-signal) 집계 산출.
- 출력(stdout): `overall`(전체 + CV 일반화 평균±분산), 각 `axes` 평균, task 수, 세그먼트 요약.
- 플래그:
  - `--json <path>`: 상세 결과(overall·CV·axes·per-task rows·세그먼트 집계)를 JSON 저장.
  - `--cv 5`: k-fold CV 실행(기본 켬).
  - `--segments`: 세그먼트 강점행렬 출력.
  - `--ruleset <cfg>`: 특정 규칙 조합으로 실행.
  - `--ablate`: 활성 규칙 각각을 off로 토글해 CV로 돌리고 한계기여를 세그먼트별로 출력(consolidation용, 비쌀 수 있음).
  - `--submission`: `data/screening_tasks.jsonl` 700개로 답안 생성 → `{project_root}/submission.csv`. meta.seed=**42**(OVERVIEW §9).

CLI 예: `python run_local.py --cv 5 --json out.json`(채점+저장), `python run_local.py --ablate --json ablate.json`(프로파일링), `python run_local.py --ruleset cand.json`(조합 실험), `python run_local.py --submission`(제출).

### 4. 재현성 검증 (게이트)

`python {code_dir}/run_local.py` 를 실행해 오류 없이 overall 점수가 나오는지 확인한다. 노트북 셀 13을 실행했을 때의 dev overall과 **대체로 일치**해야 한다(추출이 로직을 안 바꿨다는 증거). 크게 다르면 추출 오류이므로 원인을 찾아 고친 뒤 진행한다.

### 5. 첫 baseline 기록

- `{track_dir}/`를 만들고 `python run_local.py --json {baseline_scores}` 로 최초 점수 스냅샷을 저장한다.
- `{log_file}`을 `./templates/log-entry.md` 형식의 **헤더 + Iter 000(baseline)** 항목으로 생성한다. Iter 000은 "노트북 baseline 추출, 변경 없음"으로 적고 overall/axes(전체·CV 일반화 평균)를 기록한다.

### 6. Signal Catalog 생성 (①)

`{overview}`와 `data/TERMS_GUIDE.md`를 근거로 `{catalog}`를 만든다. **harness가 처리할 수 있는 신호를 유한하게 열거**한다(각 항목에 안정적 `id` 부여). 최소 커버 범위:

- **record type별 처리 규칙**: `security_alert`, `consent`(granted/revoked), `privacy_guard`, `safety_mode`, `payment_policy`, `health_share_policy`, `external_share_policy`, `enterprise_policy_recall`, `resolved_target`, `ambiguous_target`, `ambiguous_focal`, `target_changed_after_turn`, `amount_changed`, `merchant_verification`, `persistent_memory_write/recall`, `ops_memory_recall`, `memory_conflict`, `focal_marker_refs`+`focal_resolution_trace`, `routine_scope` …
- **control 결정 규칙**: 각 신호 조합이 proceed/amend/hold/ask 중 무엇을 유도하는지.
- **content_scope 규칙**: mode 선택(raw/summary/redacted/status_only/none), allowed/excluded_fields 산출.
- **plan 규칙**: verb 순서(예: guard가 dispatch보다 우선), 단계 구성, args 공개 ontology 정규화.
- **세션/메모리 규칙**: turn 간 이월(resolved target, consent, memory write) 로직.

각 항목: `{id, category, signal, 기대 판단, 대상 메서드}`.

### 7. Coverage 초기화 (①)

`{coverage}`(JSON)를 만들어 catalog 각 항목을 `status: "unhandled"`로 시작한다. baseline harness가 이미 처리하는 항목이 있으면(노트북 로직 확인) `status: "partial"`로 표시하고 근거를 적는다. `handled`/`partial`/`unhandled` 비율(coverage %)을 계산해 둔다.

### 8. Attempts / Ratchet / Backlog / Ruleset / Registry 초기화 (②④⑤⑦⑨)

- `{attempts}`: 빈 JSONL 생성(첫 줄로 Iter 000 baseline을 `decision:"baseline"`으로 기록 가능).
- `{ratchet}`: `{"cv_high_water": <baseline CV 일반화 평균>, "all_high_water": <baseline all overall>, "locked_tests": []}`. 래칫은 **CV 일반화 평균**에 건다.
- `{backlog}`: coverage의 `unhandled`/`partial` 항목을 초기 후보 큐로 나열.
- `{ruleset}`: 활성 규칙 설정. baseline은 규칙 추출 전이므로 빈 배열(`{"rules": []}`) 또는 baseline 내장 로직을 가리키는 표식으로 시작.
- `{strength_matrix}`: 빈 스켈레톤 생성(첫 consolidation에서 채움).
- `{techniques_dir}/`: 디렉터리 생성(규칙이 생길 때마다 `<name>.md` 추가).

### 9. 사람에게 보고

추출한 파일 목록, 재현성 확인 결과(노트북 vs run_local overall), baseline overall·axes, **CV 일반화 평균±분산**, fold 크기, **catalog 항목 수와 초기 coverage %**를 요약해 보고한다.

## NEXT

Read fully and follow `./step-01-measure.md`
