---
consolidate_scores: '{track_dir}/consolidate-scores.json'
ablation_out: '{track_dir}/ablation-latest.json'
---

# Step 6: Consolidate — 강점 프로파일링 & 포트폴리오 재조합 (Exploit)

`{compose_every}`반복마다 자동 실행. "새 기술 추가(탐색)"를 멈추고, **측정으로 강점을 정량화하고 가장 강한 조합으로 수렴**한다. 채점이 공짜라서 가능한 단계다.

## RULES

- 출력 언어는 항상 `{communication_language}`.
- **가정 금지, 측정만**: "이 규칙이 좋을 것"이 아니라 CV·ablation 실측으로 판단.
- 포트폴리오 변경도 **래칫(CV 일반화)·축적 테스트 하드 게이트**를 통과해야 채택.
- **신뢰 테스트(자동)**: 모든 ablation/composition 결정은 **fold 부호 일관성 ≥ `{sign_consistency}`/5** 이고 **효과 > 노이즈 플로어(baseline held-out overall의 fold 표준편차 × `{snr_k}`)** 일 때만 신뢰한다. 둘 중 하나라도 실패하면 그 효과는 노이즈로 간주해 **자동 기각**(keep/route/bench 판단에 쓰지 않는다). 사람 눈대중 금지.
- 세그먼트 판단은 support ≥ `{min_support}` 일 때만.

## PRECONDITION — 활성화 게이트 재확인

`python {code_dir}/run_local.py --readiness --json {track_dir}/readiness.json` 를 실행해 `portfolio_ready == true` 인지 확인한다. `false`면 (step-05에서 걸러졌어야 하지만) 여기서 **즉시 종료**하고 린 코어(step-01)로 돌아간다. 전제조건 미달 상태에서 ablation/composition을 돌리지 않는다.

## INSTRUCTIONS

### 1. Ablation 프로파일링 (⑦)

`python {code_dir}/run_local.py --ablate --cv 5 --json {ablation_out}` 실행. 활성 `{ruleset}`의 각 규칙을 off로 토글해 CV로 돌리고, 규칙별 **한계기여**를 세그먼트별(axis × domain × catalog-signal)로 얻는다. 각 기여는 **fold 평균±분산**으로 본다.

### 2. 강점행렬 & Technique Registry 갱신 (⑦⑨)

- `{strength_matrix}`를 최신 ablation 결과로 덮어쓴다: 규칙 × 세그먼트 → 한계기여(mean±var), 안정성 플래그.
- 각 `{techniques_dir}/<name>.md`를 **능력 기반**으로 갱신: 메커니즘 · 정량 강점프로파일(어디서 +, 어디서 −, fold 안정성) · 다른 규칙과의 상호작용(충돌/시너지) · status. **변화 서술이 아니라 현재 능력의 스냅샷.**

### 3. 규칙 분류

강점행렬로 각 규칙을 나눈다:

- **keep(전역 +)**: 모든/대부분 fold에서 순기여 +, 안정적.
- **segment-strong**: 특정 domain에서만 강함(지지 task 수 ≥ 임계). 라우팅/조건부 적용 후보.
- **redundant**: 다른 규칙과 기여가 겹쳐 빼도 점수 유지.
- **net-negative**: 순기여 −거나 불안정 → bench 후보.
- **경쟁 규칙**: 같은 catalog 신호를 다루는 둘 이상 → bake-off 대상.

### 4. Composition — 탐욕 전진선택 (⑧)

측정에 기반해 최적 규칙 부분집합을 찾는다:

1. 빈(또는 keep 확정) 집합에서 시작.
2. 후보 규칙을 하나씩 추가해 `--ruleset`로 CV 채점 → **CV 일반화 평균을 가장 올리는** 규칙을 채택. 향상 없으면 멈춤.
3. 경쟁 규칙은 같은 슬롯에서 bake-off(더 높은 CV 쪽).
4. segment-strong 규칙은 **지지 ≥ 임계이고 fold 안정적일 때만** 조건부로 포함.
5. 각 후보 조합은 **반드시 실제 실행으로 검증**(규칙 상호작용 때문에 가산성 가정 금지).

결과 = 후보 포트폴리오(`ruleset` 설정).

### 5. 검증 & 채택 (하드 게이트)

후보 포트폴리오로 `python {code_dir}/run_local.py --cv 5 --json {consolidate_scores}` + 축적 테스트(`{tests_dir}`) 실행:

- **채택 조건**: 축적 테스트 green + CV 일반화 평균이 현재 `{ratchet}.cv_high_water` **이상** + 전체 overall 하락 없음.
- 채택되면: `{ruleset}`를 후보로 교체(bench된 규칙은 `enabled:false`로, 제거 아님 — 되살릴 수 있게), `{baseline_scores}`·`{ratchet}` 상향 갱신, bench/route 사유를 각 technique 문서 status에 반영.
- 미달이면: 포트폴리오 변경을 버리고 현 상태 유지. 무엇이 왜 안 됐는지 기록.

### 6. 기록

- `{log_file}`에 **Consolidation 항목**을 append: 어떤 규칙을 keep/route/bench/제거했는지, CV 일반화 before→after, coverage·활성규칙 수 변화, 근거(강점행렬 요약).
- `{attempts}`에 consolidation 결과를 한 줄 기록(`kind:"consolidate"`).

### 7. 사람에게 보고 & 다음

포트폴리오 변화 요약(활성 규칙 수, keep/route/bench 목록), CV 일반화 before→after, 누적 진척을 보고한다. 이어서 탐색을 재개하려면 read fully and follow `./step-01-measure.md`. 여기서 **HALT**.

## NEXT

탐색 재개: `./step-01-measure.md` (또는 제출: `run_local.py --submission`)
