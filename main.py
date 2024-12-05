# main.py

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Response

from pronun_model.routers.upload_video import router as upload_video_router
from pronun_model.routers.send_feedback import router as send_feedback_router
from pronun_model.config import UPLOAD_DIR, CONVERT_MP3_DIR, CONVERT_TTS_DIR, SCRIPTS_DIR, ENABLE_PLOTTING
from pronun_model.exceptions import DocumentProcessingError, AudioProcessingError, AudioImportingError

if ENABLE_PLOTTING:
    from pronun_model.plotting.plot_waveform import plot_waveform

from pathlib import Path
import json
import uvicorn
import logging
import logging.config
import uuid
import traceback

# Context variables import
from pronun_model.context_var import request_id_ctx_var, client_ip_ctx_var

# ASGI types import
from starlette.types import ASGIApp, Receive, Scope, Send

app = FastAPI()

# Middleware to assign request_id and capture client IP
class RequestIDMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            request = Request(scope, receive=receive)
            request_id = str(uuid.uuid4())
            client_ip = request.client.host if request.client else "unknown"
            request_id_ctx_var.set(request_id)
            client_ip_ctx_var.set(client_ip)
        await self.app(scope, receive, send)

# JSON 기반 로깅 설정 적용
logging_config_path = Path(__file__).resolve().parent / "logging_config.json"  # 프로젝트 루트에 위치한 파일 경로
with open(logging_config_path, "r") as f:
    logging_config = json.load(f)

logging.config.dictConfig(logging_config)
logger = logging.getLogger("pronun_model")

# 모든 출처를 허용하는 CORS 설정 (자격 증명 포함 불가)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,  # credentials를 반드시 False로 설정
)

# Request ID 미들웨어 추가
app.add_middleware(RequestIDMiddleware)

# 라우터 포함
app.include_router(upload_video_router, prefix="/api/pronun", tags=["Video Upload & Script"])
app.include_router(send_feedback_router, prefix="/api/pronun", tags=["Feedback Retrieval"])

# 루트 엔드포인트 (선택 사항)
@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello, Selina!"}

# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug("Request received")
    try:
        response = await call_next(request)
        # responseTime 계산: 요청 처리 시간
        # FastAPI 자체적으로 responseTime을 제공하지 않으므로, 직접 측정 필요
        # 여기서는 단순 예시로 timestamp 차이를 사용
        # 실제로는 start_time을 기록하고 response 후에 차이를 계산해야 함
        response_time = response.headers.get("X-Response-Time", "unknown")  # 필요 시 설정
        logger.info("Response sent", extra={
            "errorType": "",
            "error_message": ""
        })
        return response
    except Exception as e:
        # 예외 발생 위치 추출
        tb = traceback.extract_tb(e.__traceback__)
        if tb:
            filename, lineno, func, text = tb[-1]  # 가장 마지막 스택 프레임
        else:
            filename, lineno, func, text = "unknown", 0, "unknown", "unknown"
        
        logger.error("Error processing request", extra={
            "errorType": type(e).__name__,
            "error_message": str(e)
        }, exc_info=True)
        raise e

# 예외 처리 핸들러
@app.exception_handler(DocumentProcessingError)
async def document_processing_exception_handler(request: Request, exc: DocumentProcessingError):
    logger.error("Document exception", extra={
        "errorType": type(exc).__name__,
        "error_message": str(exc)
    }, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "script를 처리하는중 오류가 발생했습니다."},
    )

@app.exception_handler(AudioImportingError)
async def audio_importing_exception_handler(request: Request, exc: AudioImportingError):
    logger.error("audio importing exception", extra={
        "errorType": type(exc).__name__,
        "error_message": str(exc)
    }, exc_info=True)
    return JSONResponse(
        status_code=400,
        content={"detail": "음성을 가져와서 변환하는중 오류가 발생했습니다."},
    )

@app.exception_handler(AudioProcessingError)
async def audio_processing_exception_handler(request: Request, exc: AudioProcessingError):
    logger.error("audio processing exception", extra={
        "errorType": type(exc).__name__,
        "error_message": str(exc)
    }, exc_info=True)
    return JSONResponse(
        status_code=400,
        content={"detail": "음성을 가져와서 처리하는중 오류가 발생했습니다."},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", extra={
        "errorType": type(exc).__name__,
        "error_message": str(exc)
    }, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다."},
    )

# 테스트 엔드포인트 추가
@app.get("/test-logging")
def test_logging():
    logger.debug("디버그 레벨 로그 테스트")
    logger.info("정보 레벨 로그 테스트")
    logger.warning("경고 레벨 로그 테스트")
    logger.error("오류 레벨 로그 테스트")
    return {"message": "로깅 테스트 완료"}

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