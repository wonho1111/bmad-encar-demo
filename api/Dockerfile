# api/Dockerfile — Cloud Run용 표준 컨테이너 이미지.
# "이 환경(파이썬 3.12)에서, 이 라이브러리를 깔고, 이렇게 실행해라"를 적어둔 설계도.
FROM python:3.12-slim

WORKDIR /app

# 1) 의존성 먼저 설치 — 코드만 바뀌면 이 레이어는 캐시돼 재설치를 건너뛴다(빌드 빠름).
# 1-a) torch는 CPU 전용판을 먼저 고정 설치한다 — 리눅스 기본 torch는 GPU(CUDA)판이라 수 GB의
#      GPU 라이브러리가 딸려온다(Cloud Run엔 GPU가 없어 전부 낭비). CPU판을 먼저 깔아두면
#      뒤의 tabpfn이 torch 요구를 "이미 충족"으로 보고 재설치하지 않는다(로컬 api venv와 동일 구성).
RUN pip install --no-cache-dir torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) 앱 코드 복사 (app 패키지만. 비밀값 .env·테스트·스크립트는 .dockerignore로 제외)
COPY app ./app

# 3) Cloud Run은 들어오는 포트를 $PORT 환경변수로 알려준다(기본 8080).
#    uvicorn이 모든 IP(0.0.0.0)의 그 포트를 듣게 한다. exec로 PID 1을 uvicorn에 넘겨
#    Cloud Run의 종료 신호(SIGTERM)를 곧바로 받게 한다(graceful shutdown).
ENV PORT=8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
