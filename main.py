# main.py

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Response

from pronun_model.routers.upload_video import router as upload_video_router
from pronun_model.routers.send_feedback import router as send_feedback_router
from pronun_model.config import ENABLE_PLOTTING
from pronun_model.utils import ensure_directories 

if ENABLE_PLOTTING:
    from pronun_model.plotting.plot_waveform import plot_waveform

from pathlib import Path
import json
import uvicorn
import logging
import logging.config

# JSON 기반 로깅 설정 적용
logging_config_path = Path(__file__).resolve().parent / "logging_config.json"  # 프로젝트 루트에 위치한 파일 경로
with open(logging_config_path, "r") as f:
    logging_config = json.load(f)

logging.config.dictConfig(logging_config)
logger = logging.getLogger("main_logger")

app = FastAPI()

# 모든 출처를 허용하는 CORS 설정 (자격 증명 포함 불가)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,  # credentials를 반드시 False로 설정
)

# 라우터 포함
app.include_router(upload_video_router, prefix="/api/pronun", tags=["Video Upload & Script"])
app.include_router(send_feedback_router, prefix="/api/pronun", tags=["Feedback Retrieval"])

@app.on_event("startup")
async def startup_event():
    """
    FastAPI 서버 시작 시 초기화 작업 수행.
    """
    logger.info("FastAPI pronun API Router Start")
    ensure_directories()  # 디렉토리 확인 및 생성

# 루트 엔드포인트 (선택 사항)
@app.get("/")
def read_root():
    logger = logging.getLogger(__name__)
    logger.info("Root endpoint accessed")
    return {"message": "Hello, Selina!"}

# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise e

# 서버 실행 (uvicorn.run()에서 log_config 지정)
if __name__ == "__main__":
    # 현재 작업 디렉터리를 스크립트의 디렉터리로 설정
    # os.chdir(os.path.dirname(os.path.abspath(__file__)))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config="logging_config.json"  # 로깅 설정 파일 지정
    )

# uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-config logging_config.json