---
current_scores: '{track_dir}/current-scores.json'
---

# Step 2: Diagnose — 병목 진단 & 후보 선정 [체크포인트]

이 스킬의 핵심. **catalog(탐색공간) × 실패 데이터(우선순위) × attempts(신규성 게이트)** 로 다음 후보를 기계적으로 도출한다. 모델이 즉흥으로 고르지 않는다.

## RULES

- 출력 언어는 항상 `{communication_language}`.
- 후보는 반드시 **일반화 가능한 규칙**. 특정 task_id/session_id 정답 주입은 후보 자격 없음.
- 한 반복에 **후보 하나만**.
- **신규성은 협상 불가**: `{attempts}`에 같은 지문이 있으면 그 후보는 탈락.

## INSTRUCTIONS

### 1. 실패를 catalog 항목에 매핑

`{current_scores}`의 per-task `rows`를 원본(`data/dev_tasks.jsonl`)·정답(`data/dev_answers.json`)과 대조해 점수를 잃은 task를 찾고, **게이팅상 가장 먼저 깨진 축**으로 원인을 규정한다(focal→target→control→scope/policy/plan 순). 각 실패를 `{catalog}`의 항목(signal id)에 연결한다: "이 task는 `focal_marker_refs` 미처리로 focal이 틀림" 처럼.

catalog에 없는 새 실패 패턴이 보이면 **catalog에 항목을 추가**하고 coverage에 `unhandled`로 등록한다(탐색공간이 데이터로 확장됨).

### 2. 게이팅 파급 반영 "기회 점수"로 후보 랭킹

각 catalog 항목(주로 `unhandled`/`partial`)에 대해, 그걸 처리했을 때 회복 가능한 점수를 추정한다:

- focal 관련 항목: focal(0.18) + 그 task의 downstream(target·control·scope·policy·plan)이 0→회복될 여지 → 상한 큼.
- 이미 게이트 통과한 task의 scope/policy 항목: 해당 축 가중치 내에서만 → 상한 작음.

`기회점수 ≈ Σ(항목이 걸린 task들에서 회복 가능한 축가중치×개선폭)`. 랭킹용 추정이면 충분.

### 3. 신규성 게이트 (② — 하드 체크)

상위 후보 각각에 대해 **지문**을 만든다: `<대상메서드>:<signal_id>:<규칙종류 요약>`. `{attempts}`를 조회해:

- 동일 지문이 이미 있으면(성공이든 실패든) → **탈락**. 실패했던 접근을 반복하려면 지문이 실제로 달라야 한다(다른 규칙종류/다른 신호결합). 왜 다른지 한 줄로 적는다.
- 통과한 후보만 후보로 남긴다.

이 게이트를 통과 못 해 후보가 고갈되면 §5(수확체감 방어)로 간다.

### 4. 최우선 후보 확정 & 백로그 갱신

`{backlog}`를 기회점수 내림차순으로 갱신하고 **최우선 후보 1개**를 확정한다. `{diagnosis_file}`에 기록:

- **가설**: "harness의 X를 바꾸면 catalog 항목 `<id>`(N개 task)가 회복되어 약 +Z 기대"
- **대상 메서드** 및 **새 규칙 모듈 경로**(예: `{rules_dir}/consent_revoked.py`)
- **지문**: `<대상메서드>:<signal_id>:<규칙종류>` (신규 확인됨)
- **일반화 근거**: 공개 예시 암기가 아니라 새 task에도 통하는 이유 한 줄
- **회귀 위험**: 지금 맞는 어떤 task를 깰 수 있는지 + 어떤 단위 테스트로 잠글지

### 5. 수확체감 방어 (막다른 길 금지)

최우선 후보 기대 이득이 미미(< +0.005)하거나 신규성 게이트로 고갈되면 진단을 넓힌다 — 절대 멈추지 않는다:

- catalog를 도메인별(payment/health/privacy/iot/message)로 더 잘게 재분할해 숨은 미처리 항목 발굴.
- **CV gap 항목**: 전체 점수는 높은데 CV 일반화 평균이 낮거나 fold 분산이 큰 축/domain → "과적합 되돌리기/일반화"를 후보로.
- 구조적 후보: 세션 메모리 이월, plan args ontology 정규화 정합, 규칙 실행 순서 재정렬.
- 그래도 없으면 남은 후보와 각 기대 이득을 사람에게 제시하고 전략을 묻는다.

### 6. 체크포인트 — HALT

최우선 후보(가설·대상모듈·지문·기대이득·회귀위험·일반화근거)와 차순위 2~3개, 현재 coverage %를 요약해 제시하고 **HALT**. 승인/수정/다른 후보 선택을 기다린다.

## NEXT

승인되면 read fully and follow `./step-03-improve.md`
