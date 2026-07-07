---
current_scores: '{track_dir}/current-scores.json'
---

# Step 1: Measure — 현재 상태 채점

## RULES

- 출력 언어는 항상 `{communication_language}`.
- 측정은 **읽기 전용**이다. harness.py를 여기서 고치지 않는다.

## PRECONDITION

`{code_dir}/run_local.py`와 `{baseline_scores}`가 존재하는지 확인. 없으면 부트스트랩이 안 된 것 → `./step-00-bootstrap.md`로 간다.

## INSTRUCTIONS

1. 현재 harness(활성 `{ruleset}`)를 CV로 채점한다: `python {code_dir}/run_local.py --cv 5 --json {current_scores}`
2. 결과를 읽어 다음을 파악한다:
   - `overall` (전체) 와 **CV 일반화 평균±분산**
   - axes 평균: focal, target, control, content_scope, policy, plan
   - per-task `rows` (task별 score와 axes)
   - 세그먼트 요약(domain별 약점)
3. `{baseline_scores}`(직전 채택 스냅샷)와 비교해 현재가 그와 같은지 확인한다. 같아야 정상. 다르면 미커밋 변경 → 사람에게 알리고 의도를 확인한다.
4. 간단 요약을 출력한다: 현재 overall(전체)·CV 일반화 평균과 가장 낮은 축·domain 2~3개.

## NEXT

Read fully and follow `./step-02-diagnose.md`
