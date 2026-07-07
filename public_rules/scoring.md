1. 리더 보드 (예선)
평가 산식은 참가자가 제출한 700개 Public Screening 답안을 서버 보관 정답과 비교하여 산출한 overall 점수입니다. 
점수가 높을수록 우수합니다.
Public leaderboard 점수는 공개 screening task에 대한 점수입니다. 
공개 screening은 제출 형식, 기본 동작, 문제 이해도를 확인하기 위한 리더보드로 활용됩니다. 
예선 종료 후 상위권 참가자는 주최측 안내에 따라 동일한 아이디어를 구현한 harness.py 실행 가능본을 추가 제출해야 할 수 있으며, 이 코드는 주최측 검증 환경에서 별도 비공개 task stream으로 재현성 및 일반화 성능을 확인할 수 있습니다.
예선 제출 방식은 다음과 같습니다.
				1. 참가자는 제공된 screening_tasks.jsonl의 700개 과제에 대해 답안을 생성합니다.

				2. 생성된 answer JSON 전체를 submission.csv의 submission 컬럼 단일 셀에 저장합니다.

				3. DACON 서버는 submission.csv를 업로드받아 JSON을 복원합니다.

				4. 서버 보관 정답과 비교하여 700개 Public Screening 기준 overall 점수를 산출합니다.

				5. 산출된 overall 점수가 public leaderboard에 반영됩니다.

제출 파일 구조는 다음과 같습니다.
파일명: submission.csv
컬럼명: submission
데이터 행: 1행
인코딩: UTF-8
내용: submission 컬럼의 단일 셀에 answer JSON 전체 저장
JSON 파일 직접 제출은 지원하지 않습니다.
예시:
submission
"{""schema"":""scpc.final.answer.v1"",""meta"":{...},""answers"":{...}}"
세부 제출 형식은 데이터 페이지의 sample_submission.csv, submission_schema.json, TERMS_GUIDE.md를 참고해 주시기 바랍니다.



2. 평가 방식
참가자가 submission.csv를 업로드하면 서버는 CSV의 submission 셀에 포함된 JSON을 복원하여 채점합니다. 
채점은 Public Screening 평가 대상 과제 700개를 기준으로 진행되며, 서버에 보관된 비공개 정답과 비교하여 overall 점수 하나를 산출합니다.
1차 예선 리더보드에는 제출물의 overall 점수가 반영됩니다.
예선 종료 후 상위권 참가자는 주최측 안내에 따라 harness.py 코드 실행 가능본과 README를 제출해야 할 수 있습니다. 
제출된 코드는 재현성 검증 및 내부 검증 절차를 거치며, 검증 결과에 따라 다음 단계 진출 여부가 확정됩니다.
상위권 검증 단계에서는 예선 제출물의 재현 가능성, 제공된 fixed SLM interface 사용 여부, 외부 모델/API 사용 여부, 하드코딩 여부 등을 확인할 수 있습니다. 
필요 시 주최측 내부 평가 환경에서 별도의 비공개 과제를 활용한 추가 검증이 진행될 수 있습니다.
따라서 공개 screening 점수를 높이는 것만이 아니라, 같은 harness가 새로운 task에서도 작동하도록 설계하는 것이 중요합니다. 
공개 dev 정답을 보고 제출 형식과 필드 의미를 학습하는 것은 허용되지만, 특정 task id, 공개 예시 문장, 공개 screening 항목에만 맞춘 답안표를 만드는 방식은 상위권 검증에서 재현성 또는 일반화 문제가 될 수 있습니다.