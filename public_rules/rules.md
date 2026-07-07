1. 참여 규칙
개인(1인)으로만 참여할 수 있습니다.
개인 참가 방법 : 팀 신청 없이, 자유롭게 제출탭에서 제출 가능합니다.
동일인의 다계정 참가 등록은 금지되며, 적발 시 부정행위로 처리됩니다.
SCPC 알고리즘 챌린지와 중복하여 참가 불가합니다.
  

2. API, 외부 데이터 및 사전 학습 모델 관련 규칙
2-1. 추론 모델 고정
본 과제에서는 참가자에게 별도 대형 모델 설치를 필수로 요구하지 않습니다. 
공개 안내의 fixed SLM interface는 task evidence, risk, redaction, confirmation 관련 신호를 보조적으로 활용하기 위한 고정 interface입니다.
FixedSLMClient는 정답을 직접 반환하는 모델이 아닙니다. 최종 답안의 focal_id, target, control, content_scope, policy, plan_events는 참가자의 Harness logic이 직접 구조화해야 합니다.
summarize_task()는 task를 읽고 위험 신호, 삭제 또는 축약 필요성, 사용자 확인 필요성 같은 evidence를 일정한 형식으로 요약해 주는 보조 함수로 이해하면 됩니다. 
이 출력은 정답표가 아니며, 참가자는 해당 evidence를 자신의 rule, parser, session memory, plan builder와 결합해 최종 answer를 만들어야 합니다. 
즉, fixed SLM은 "답을 대신 써 주는 장치"가 아니라 "agent가 task를 더 안정적으로 읽도록 돕는 같은 조건의 보조 입력"입니다.
공식 실행 조건은 다음과 같습니다.
제공 interface: FixedSLMClient
제출 JSON의 meta.fixed_slm_policy: local_fixed_slm_only
제출 JSON의 meta.model_id: scpc-final-fixed-slm-local-facade
외부 유료 LLM API, 네트워크 호출, 임의 외부 모델 사용 금지
권장 기본값: temperature=0.0, seed=42
상위권 코드 검증에서 사용하는 Harness는 FinalHarness.answer_task(task, session) 형태입니다. 
참가자는 task의 prompt, device_state, records, visible_history, 이전 session 상태 등을 바탕으로 판단하고, 필요한 경우 FixedSLMClient facade가 제공하는 evidence 신호를 보조적으로 활용해 다음 형식의 답안을 반환해야 합니다.
class FinalHarness:
    def __init__(self):
        self.slm = FixedSLMClient()
        self.user_memory = {}

    def answer_task(self, task, session):
        evidence = self.slm.summarize_task(task)
        answer = build_structured_answer(task, session, evidence)
        return answer
답안 형식:
{
    "focal_id": "...",
    "target": "...",
    "control": "proceed|amend|hold|ask",
    "content_scope": {...},
    "policy": {...},
    "plan_events": [...]
}
권장 구현 구조는 다음과 같습니다.
choose_focal: 현재 요청에서 중심 object를 고릅니다.
infer_target: 최종 수신처, 앱, 채널, 장치, 메모리 저장소 등을 정합니다.
decide_control: proceed, amend, hold, ask 중 하나를 결정합니다.
build_content_scope: 어떤 정보는 쓰고 어떤 정보는 제외할지 정합니다.
build_policy: 위험 신호, 위반 가능성, 확인 필요 여부를 정리합니다.
build_plan_events: 읽기, 확인, 요약, 삭제, 전송, 보류, 업데이트 같은 계획 단계를 만듭니다.
update_session_memory: 같은 실행 흐름에서 이후 task가 참고할 정보를 저장합니다.
제공 seline은 위 구조를 한 파일 안에서 실행해 submission.csv를 만드는 예시입니다. 
baseline은 제출 형식과 구현 흐름을 보여주는 약한 출발점이며 높은 점수를 위해서는 참가자가 각 모듈의 판단 로직을 직접 개선해야 합니다.
상위권 참가자는 제출 종료 후 재현성 검증을 위해 사용한 Harness 코드, 실행 방법, 주요 규칙·프롬프트·파싱 로직, fixed SLM facade 활용 방식을 제출해야 할 수 있습니다. 
제출 CSV의 metadata가 공식 interface 사용을 주장하더라도, 실제 생성 과정이 외부 모델/API/수동 라벨링에 의존한 경우 평가 기준 위반으로 처리될 수 있습니다.

2-2. 개발 도구 사용
Harness 코드 작성, 디버깅, 개선 등 개발 단계에서는 AI 코딩 도구를 사용할 수 있습니다. 
단, 최종 제출 답안을 생성하는 과정에서는 주최측이 제공한 데이터와 허용된 fixed SLM interface 사용 기준을 따라야 하며, 참가자 간 성능 차이는 Harness 설계와 구현 방식에서 발생해야 합니다.

2-3. 데이터 활용 기준
대회에서 제공하는 데이터와 공개된 연습용 dev 데이터는 문제 구조 이해, 제출 형식 확인, 로컬 테스트에 활용할 수 있습니다.
다만 평가 대상 과제의 정답이나 특정 패턴을 직접 추정하거나, 특정 평가 과제에만 맞춘 방식으로 답안을 구성하는 행위는 허용되지 않습니다.
권장되는 활용 방식은 dev task와 dev answer를 통해 "답안 JSON이 어떤 구조를 가져야 하는지", "각 필드가 어떤 역할을 하는지", "내 harness가 스키마를 만족하는지"를 점검하는 것입니다. 
공개 dev 예시에서 보이는 특정 문장, record 값, object 순서를 그대로 외워 screening 또는 검증 task에 적용하는 방식은 권장하지 않습니다.

2-4. 하드코딩 금지
특정 task_id, session_id 또는 평가 항목에 대한 정답을 코드에 직접 입력하거나, 일반화되지 않은 방식으로 평가 과제를 푸는 행위는 무효 처리될 수 있습니다.
참가자는 다양한 과제에 적용 가능한 일반화된 Agent Harness를 설계·구현해야 합니다.


3. 코드 및 PPT 제출 규칙
3-1. 예선 제출물
예선 단계에서는 지정된 형식의 submission.csv 파일을 제출해야 합니다.
submission.csv는 다음 조건을 만족해야 합니다.
파일명: submission.csv
UTF-8 인코딩
컬럼명: submission
데이터 행: 1행
submission 셀 안에 answer JSON 전체 포함
JSON 최상위 구조는 submission_schema.json을 따름
JSON 파일 직접 제출은 지원하지 않습니다. 참가자는 최종 제출 파일로 submission.csv만 업로드해야 합니다.
상위권 참가자는 주최측 안내에 따라 harness.py 코드 실행 가능본과 README를 제출해야 할 수 있습니다.
제출된 코드는 재현성 검증을 거치며, 검증 결과에 따라 최종 진출 여부가 확정됩니다. 
이 단계에서 주최측 내부 평가 환경의 별도 비공개 과제를 활용한 추가 검증이 진행될 수 있습니다.
상위팀 코드 제출의 세부 형식과 제출 방법은 추후 주최측 안내에 따릅니다.

3-2. 본선 제출물
본선 단계에서는 예선에서 사용한 Harness 설계 및 구현 내용을 바탕으로 솔루션 발표자료(PPT)와 코드를 제출해야 합니다.
발표자료에는 Harness의 설계 의도, 전체 아키텍처, 문제 해결 전략, fixed SLM evidence 활용 방식, 세션 메모리 관리 방식, 한계점 및 개선 방향 등을 포함하는 것을 권장합니다. 
발표자료 분량은 15페이지 이내로 작성하며, 본선에서는 발표와 질의응답이 함께 진행됩니다.


4. 유의 사항
1일 최대 제출 횟수: 5회 (단, 대회 운영 상황 및 점수 분포에 따라 제출 횟수는 조정될 수 있습니다)
제출 파일은 반드시 submission.csv 형식이어야 하며, JSON 파일을 직접 제출하는 방식은 지원하지 않습니다.
CSV 내부의 JSON이 파싱되지 않거나, 제출 스키마를 만족하지 않거나, 필수 과제 ID가 누락된 경우 제출 오류 또는 낮은 점수로 처리될 수 있습니다.
dev_answers.json은 일부 dev_tasks.jsonl 문제에 대한 참조 답안 예시입니다. 전체 dev 문제의 상세 해설이나 screening 정답이 아니며, 제출 구조와 로컬 동작을 점검하기 위한 용도입니다.
dev_answers.json은 screening 답안 생성이나 최종 제출 파일에 포함해서는 안 됩니다. 
실제 리더보드 평가는 screening_tasks.jsonl의 700개 과제에 대한 submission.csv 제출 결과로 산출됩니다.
사용 가능 언어: Python
대회 기간과 참가자들의 점수 분포 등을 고려하여, 주최측의 요청에 따라 일정 기간 동안 '코드 공유' 탭이 일시적으로 비활성화될 수 있습니다.
모든 csv 형식의 데이터와 제출 파일은 UTF-8 인코딩을 적용합니다.
모델 학습과 추론에서 평가 데이터셋 정보 활용(Data Leakage)시 실격 또는 본선 진출이 불가능합니다.
평가용 이미지 또는 지문을 수작업으로 라벨링하거나, 이를 기반으로 정답을 직접 추정하여 학습 데이터처럼 사용하는 행위
평가 데이터셋에서 특정 패턴이나 정답 분포를 분석해 모델 구조, 전처리 방식, 정답 후보 설정 등에 반영하는 행위 등
모든 학습, 추론의 과정 그리고 추론의 결과물들은 정상적인 코드를 바탕으로 이루어져야하며, 비정상적인 방법으로 얻은 제출물들은 적발 시 규칙 위반에 해당됩니다.
최종 순위는 선택된 파일 중에서 채점되므로 참가자는 제출 창에서 자신이 최종적으로 채점 받고 싶은 파일 1개를 선택해야 함
대회 직후 공개되는 Private 랭킹은 최종 순위가 아니며 본선 진행 후, 최종 수상자가 결정됨
데이콘은 부정 제출 행위를 금지하고 있으며 데이콘 대회 부정 제출 이력이 있는 경우 평가가 제한됩니다. 자세한 사항은 아래의 링크를 참고해 주시기 바랍니다.
https://dacon.io/notice/notice/13

 

5. 토론(질문)
대회 운영 및 데이터 이상에 관련된 질문 외에는 답변을 드리지 않고 있습니다. 기타 질문은 토론 페이지를 통해 자유롭게 토론해주시기 바랍니다.
데이콘 답변을 희망하는 경우 토크 게시글 댓글로 질문을 올려 주시기 바랍니다.
예) [DACON 답변 요청] 시상식은 언제 열리나요?