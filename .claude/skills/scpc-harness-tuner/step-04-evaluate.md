---
current_scores: '{track_dir}/current-scores.json'
after_scores: '{track_dir}/after-scores.json'
---

# Step 4: Evaluate — 재채점 · 래칫 · 회귀차단 · keep/revert

결정은 데이터로. "좋아졌을 것 같다"가 아니라 실제 점수·테스트로 판단한다.

## RULES

- 출력 언어는 항상 `{communication_language}`.
- **래칫과 축적 테스트는 하드 게이트**다. 통과 못 하면 KEEP 불가.

## INSTRUCTIONS

### 1. 축적 단위 테스트 실행 (④ — 하드 게이트)

`{tests_dir}` 전체를 실행한다(`pytest {tests_dir}` 등). **하나라도 깨지면** 이번 변경이 이전에 잠근 규칙을 회귀시킨 것 → **즉시 REVERT 후보**. 새로 추가한 테스트 포함 전부 green이어야 다음으로 간다.

### 2. 재채점

`python {code_dir}/run_local.py --cv 5 --json {after_scores}` 실행(활성 ruleset에 새 규칙 등록된 상태).

### 3. 델타 계산

`{baseline_scores}`(직전 채택) 대비 `{after_scores}`:

- overall 델타: **전체 / CV 일반화 평균 각각**.
- axes 델타: focal/target/control/scope/policy/plan.
- **task 회귀검사**: per-task rows 대조 → 오른 task 수 / 내린 task 수, 내린 task id와 원인 축.

### 4. 래칫 검사 (④ — 하드 게이트)

`{ratchet}`의 `cv_high_water`와 비교:

- `after`의 **CV 일반화 평균이 high-water보다 낮으면** → 래칫 위반 → **REVERT**(전체 overall이 아무리 올라도). 과적합을 구조적으로 차단.
- 같거나 높으면 통과. (단일 fold만 튀는 개선은 CV 평균에서 걸러진다)

### 5. keep / revert 결정

- **KEEP**: 축적 테스트 green + 래칫(CV) 통과 + 전체 overall 상승 + 심각한 회귀 없음.
- **REVERT**: 테스트 깨짐 / 래칫 위반 / 전체 overall 하락 / 회귀 손실이 이득 초과.
- **애매**(전체 + but CV 정체, 소수 회귀 등): 델타 표를 사람에게 제시하고 결정을 묻는다.

### 6. 결정 반영

- **KEEP**:
  - `{after_scores}` → `{baseline_scores}`로 승격.
  - 새 규칙을 `{ruleset}`에 **활성(enabled)** 으로 등록(id·순서·파라미터). 이 규칙은 이제 풀의 일원 → 다음 consolidation에서 ablation 대상.
  - `{ratchet}`의 `cv_high_water`/`all_high_water`를 새 값으로 **갱신(상향만)**, 새 테스트 경로를 `locked_tests`에 추가.
  - `{coverage}`에서 해당 catalog 항목을 `handled`(또는 `partial`)로 표시하고 규칙모듈·iter·축영향 기록.
  - `{techniques_dir}/<name>.md`에 이 기술의 초기 능력 명세를 만든다(메커니즘·잠정 강점·상호작용). 정량 프로파일은 다음 consolidation에서 채워진다.
- **REVERT**:
  - `{track_dir}/snapshots/preNNN/`로 `harness.py`·rules를 되돌린다. 새로 추가한 규칙모듈/테스트도 제거(또는 비활성). baseline·ratchet 불변.
  - 되돌려도 이 시도는 남긴다(다음 진단의 자산).

### 7. Attempts 기록 (② — 항상)

KEEP이든 REVERT든 `{attempts}`에 한 줄 append: `{iter, fingerprint, target_method, signal_id, rule_summary, delta_all, delta_cv, decision}`. 이게 신규성 게이트의 근거가 된다.

## NEXT

Read fully and follow `./step-05-log.md`
