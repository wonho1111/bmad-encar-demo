# api/Dockerfile — Cloud Run용 표준 컨테이너 이미지.
# "이 환경(파이썬 3.12)에서, 이 라이브러리를 깔고, 이렇게 실행해라"를 적어둔 설계도.
FROM python:3.12-slim

WORKDIR /app

# 1) 의존성 먼저 설치 — 코드만 바뀌면 이 레이어는 캐시돼 재설치를 건너뛴다(빌드 빠름).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) 앱 코드 복사 (app 패키지만. 비밀값 .env·테스트·스크립트는 .dockerignore로 제외)
COPY app ./app

# 3) Cloud Run은 들어오는 포트를 $PORT 환경변수로 알려준다(기본 8080).
#    uvicorn이 모든 IP(0.0.0.0)의 그 포트를 듣게 한다. exec로 PID 1을 uvicorn에 넘겨
#    Cloud Run의 종료 신호(SIGTERM)를 곧바로 받게 한다(graceful shutdown).
ENV PORT=8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
