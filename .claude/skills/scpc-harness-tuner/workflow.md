---
project_root: '/Users/giyoung/Desktop/code/scpc'
data_dir: '{project_root}/data'
notebook: '{project_root}/data/SCPC2026_Final_baseline.ipynb'
overview: '{project_root}/OVERVIEW.md'
code_dir: '{project_root}/harness'
track_dir: '{project_root}/improvement'
log_file: '{project_root}/improvement/LOG.md'
baseline_scores: '{project_root}/improvement/baseline_scores.json'
diagnosis_file: '{project_root}/improvement/diagnosis-latest.md'
catalog: '{project_root}/improvement/signal-catalog.md'
coverage: '{project_root}/improvement/coverage.json'
attempts: '{project_root}/improvement/attempts.jsonl'
backlog: '{project_root}/improvement/backlog.md'
ratchet: '{project_root}/improvement/ratchet.json'
rules_dir: '{project_root}/harness/rules'
tests_dir: '{project_root}/harness/tests'
ruleset: '{project_root}/improvement/ruleset.json'
strength_matrix: '{project_root}/improvement/strength-matrix.json'
techniques_dir: '{project_root}/improvement/techniques'
folds: '{project_root}/improvement/folds.json'
compose_every: 3
communication_language: '한국어'
---

# SCPC Harness Tuner — 지속 개선 워크플로우

**목표:** SCPC 답안 harness를 데이터가 가리키는 병목부터 하나씩 고쳐 로컬(그리고 리더보드) 점수를 지속적으로 끌어올린다. 매 반복마다 **무엇을 바꿨고 점수가 어떻게 달라졌는지**를 남긴다.

**CRITICAL:** 스텝이 "read fully and follow step-XX"라고 하면 그 스텝을 읽고 그대로 따른다. 예외 없음.

## 왜 "체크리스트"가 아니라 "루프"인가

focal→control 같은 고정 순서로 짜면 그게 끝나는 순간 개선이 막힌다. 이 스킬은 대신 **로컬 채점기의 per-task·per-axis 진단을 엔진**으로 삼는다. 병목은 매 반복 데이터가 알려주므로, focal이 탄탄해지면 진단은 자연히 target → control 엣지케이스 → content_scope F1 → policy → plan 순서로 옮겨간다. **소재가 마르지 않는다.**

## 채점 구조를 반드시 이해하고 시작 (OVERVIEW.md §7)

채점은 **계층적(gated)** 이다:

- `focal_id`가 틀리면 → `target`, `control` = 0 (focal이 하드 게이트)
- `target` 또는 `control`이 틀리면 → `content_scope`, `policy`, `plan` = 0 (`dependent = target × control`로 곱해짐)

가중치: focal 0.18 / control 0.18 / plan 0.18 / content_scope 0.17 / policy 0.13 / target 0.12 / semantic_response 0.04.

**함의:** 어떤 개선의 실제 가치는 그 축 점수뿐 아니라 **게이팅 파급**까지 합쳐야 한다. focal 하나를 살리면 downstream 5개 축이 0→회복될 수 있다. 후보 선정(step-02)은 이 파급을 계산한 **기회 점수**로 랭킹한다.

## 개선을 "vibes"가 아니라 "래칫 탐색"으로 만드는 4개 장치 (핵심)

개선의 "무엇을 고칠까"를 매 반복 모델의 즉흥에 맡기지 않는다. 아래 4개가 **신규성·전진·누적**을 기계적으로 강제한다. 모델은 이 상태 파일들을 **게이트로 복종**한다 — 단순 참고가 아니다.

### ① Signal Catalog — 개선을 유한한 탐색공간으로 고정 (`{catalog}`, `{coverage}`)
부트스트랩에서 `TERMS_GUIDE`의 온톨로지를 **유한한 항목표**로 만든다: 모든 record type × control 결정 × scope mode × plan 순서 규칙 × args ontology = "harness가 처리해야 할 신호 하나". `{coverage}`가 각 항목의 상태(unhandled/handled·규칙모듈·축영향)를 든다. **개선 = 이 목록을 소진하는 것**, coverage %가 고도화의 정량 지표.

### ② Attempts Registry — 이전 시도 반복을 물리적으로 차단 (`{attempts}`)
모든 시도의 **지문**(`대상메서드:신호id:규칙종류`) + 결과(delta·KEEP/REVERT)를 append. step-02에서 후보 확정 전 **지문 조회가 하드 게이트**: 겹치면 후보 자격 없음. 실패한 접근의 변형도 다른 지문이어야 통과.

### ③ Rule-module 아키텍처 — 고도화를 코드 자산으로 (`{rules_dir}`, `{tests_dir}`)
개선은 **규칙 모듈 1개 + 단위 테스트 1개** 추가/수정으로 구현한다(점진적 전환: 건드리는 영역부터 모듈로 추출). FinalHarness는 규칙들을 정렬 실행하는 얇은 엔진이 된다. 개선이 리뷰·테스트 가능한 누적 코드가 된다.

### ④ Regression Ratchet — 되돌아가지 않는 전진 (`{ratchet}`, 축적된 단위 테스트)
KEEP마다 그 시점 **CV 일반화 평균**(아래 ⑥)을 high-water mark로 잠금. 이후 변경이 래칫 아래로 내려가거나 축적된 단위 테스트를 깨면 step-04가 **자동 거부**. 진척은 단조 증가.

**매 반복 강제 흐름:** catalog 미처리 항목/실패클러스터 → attempts 신규성 게이트 → 규칙모듈+테스트 구현 → 래칫·테스트 회귀차단 → coverage·attempts·ratchet 갱신.

## 확장: 공짜 채점을 활용한 포트폴리오 탐색 (Explore/Exploit)

로컬 채점은 결정적이고 API 비용이 없다 → **여러 번 돌려 정량 비교**가 공짜다. 이를 활용해 선형 언덕오르기를 넘어선다.

### ⑤ 규칙풀 + 켜짐설정 = "버전" (`{ruleset}`)
harness는 규칙 모듈들의 **풀**이고, "버전"은 어떤 규칙을 켰는지의 **설정(`{ruleset}`)**이다. 규칙마다 안정적 `id`가 있어 **on/off·순서·파라미터**로 무수한 버전을 값싸게 만든다. `run_local.py --ruleset <cfg>`로 임의 조합을 채점.

### ⑥ 교차검증(k-fold) — "여러 번 돌려 정량 판단" (`{folds}`)
단일 holdout 대신 dev를 `session_id` 기준 **5겹 CV**로 나눈다. 일반화 점수 = 각 fold를 held-out으로 채점한 overall의 **평균**. 기술의 기여는 **평균±분산**으로 본다. 래칫은 이 **CV 일반화 평균**에 건다(단일 holdout보다 안정적).

### ⑦ Ablation 프로파일링 — "어디가 강한지" 측정 (`{strength_matrix}`)
각 규칙을 껐다 켜며 CV로 돌려, 규칙의 **한계기여를 세그먼트별(axis × domain × catalog-signal)로** 측정한다. "이 기술은 payment focal에 +, health scope에 −" 가 추측이 아니라 측정값이 된다. consolidation(step-06)에서 갱신.

### ⑧ Composition — "강점만 조합" (step-06, `{compose_every}`반복마다 자동)
규칙풀에서 CV 일반화 점수를 최대화하는 **부분집합을 탐욕 전진선택**으로 찾고 **실제 실행으로 검증**한다. 같은 신호를 다루는 경쟁 규칙은 bake-off로 승자 선택. 순기여 음수/중복 규칙은 뺀다.

### ⑨ Technique Registry — 변화가 아니라 "기술 기반" 서술 (`{techniques_dir}`)
`{techniques_dir}/<name>.md`에 각 기술을 **능력 명세**로 기록한다: 메커니즘 · 최신 정량 강점프로파일(어디서 강/약, fold 간 안정성) · 다른 규칙과의 상호작용 · 현재 status(active/benched). 체인지로그가 아니라 **살아있는 프로파일** — consolidation에서 최신 측정으로 덮어쓴다.

**과적합 가드레일(공짜라서 오히려 더 중요):**
- **최소 지지(support)**: 세그먼트 task 수가 임계(기본 8) 미만이면 그 세그먼트로 라우팅/판단하지 않는다. 3~4개짜리 셀 최적화는 순수 과적합.
- **fold 안정성**: 모든 fold에서 +이고 분산이 작은 기여만 신뢰. 한 fold만 튀는 건 노이즈.
- **래칫은 composite에도 하드 게이트**: 탐색 강도가 셀수록 CV 일반화 래칫이 방어선.

**Explore/Exploit 교대:** step 01–05는 "탐색(새 기술 추가)", step-06은 "활용(강점 재조합 + 프로파일 갱신)". `{compose_every}`반복마다 자동으로 step-06을 돈다.

## 절대 원칙 — 하드코딩·과적합 금지 (실격 요소)

- 특정 `task_id`/`session_id`에 정답을 직접 넣거나, 공개 예시 문장·record 값을 암기하는 변경은 **금지**. 규칙 위반이자 상위권 검증(비공개 task)에서 무너진다.
- 모든 개선은 **처음 보는 task에도 적용되는 일반화된 규칙/파서/로직**이어야 한다.
- 이 원칙은 step-03(구현)과 step-05(기록)에서 **하드 게이트**로 검사한다.

## 과적합 조기 감지 (k-fold CV)

dev 120개를 `session_id` 기준 **5겹 CV**(⑥)로 나눠 각 fold를 held-out으로 채점한 overall의 **평균**을 일반화 점수로 쓴다. **전체 점수는 오르는데 CV 일반화 평균이 정체/하락하면 과적합 경보** → 되돌리거나 더 일반화한다. dev가 120개뿐이라 신호는 약하지만, 단일 holdout보다 안정적이고 fold 분산으로 신뢰도를 함께 본다.

## 워크플로우 아키텍처 (bmad 스타일)

step-file 아키텍처로 규율 있게 실행한다:

- **Micro-file**: 각 스텝은 self-contained. 그대로 따른다.
- **Just-In-Time 로딩**: 현재 스텝 파일만 읽는다. 여러 스텝을 동시에 읽지 않는다.
- **순차 강제**: 순서대로, 건너뛰지 않는다.
- **상태 추적**: LOG.md와 baseline_scores.json로 진행 상태를 영속화한다.
- **체크포인트**: step-02(후보 승인)에서 HALT하고 사람 입력을 기다린다.

### 스텝 처리 규칙

1. **완독**: 실행 전 스텝 파일 전체를 읽는다.
2. **순서 준수**: 섹션을 순서대로 실행한다.
3. **체크포인트 대기**: 승인 지점에서 멈추고 사람을 기다린다.
4. **다음 로드**: 지시가 있을 때만 다음 스텝을 읽고 따른다.

## 초기화 시퀀스

### 1. 컨텍스트 로딩

- `{overview}`를 읽어 대회 목표·데이터·채점 구조를 파악한다 (이 스킬의 기준 문서).
- `{project_root}/CLAUDE.md`가 있으면 읽는다.
- **출력 언어는 항상 `{communication_language}`.**

### 2. 부트스트랩 여부 판단

`{code_dir}/harness.py`, `{code_dir}/run_local.py`, `{baseline_scores}`, `{catalog}`, `{coverage}`, `{attempts}`, `{ratchet}`, `{ruleset}`, `{folds}`가 모두 존재하고 유효하면 → 인프라가 이미 있는 것. **step-01로 간다.**

하나라도 없으면 → 최초 실행. **step-00으로 가서 인프라를 구축**한다.

### 3. 첫 스텝 실행

- 부트스트랩 필요: read fully and follow `./step-00-bootstrap.md`
- 이미 구축됨: read fully and follow `./step-01-measure.md`
