# pronun_model/config.py

from dotenv import load_dotenv
from pathlib import Path
import os
from fastapi import HTTPException
import logging

# 모듈별 로거 생성
logger = logging.getLogger(__name__)  # 'pronun_model.config' 로거 사용

# .env 파일에서 환경 변수 로드
load_dotenv()

# 추가 설정
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 60))  # 기본값 60초
AVERAGE_WPM = int(os.getenv("AVERAGE_WPM", 100))  # 기본값 100 WPM

# Docker 환경 감지 및 경로 설정
try:
    with open('/proc/1/cgroup', 'rt') as f:
        cgroup_content = f.read()
    if 'docker' in cgroup_content:
        # Docker 환경
        BASE_DIR = Path("/app")
        logger.info("Docker 환경으로 감지되었습니다.")
        logger.debug(f"BASE_DIR 설정: {BASE_DIR}")
    else:
        # 로컬 환경
        BASE_DIR = Path(__file__).resolve().parent.parent
        logger.info("로컬 환경으로 감지되었습니다.")
        logger.debug(f"BASE_DIR 설정: {BASE_DIR}")
except FileNotFoundError:
    # 로컬 환경
    BASE_DIR = Path(__file__).resolve().parent.parent
    logger.info("로컬 환경으로 간주합니다. 기본 경로로 설정합니다.")
    logger.debug(f"BASE_DIR 설정: {BASE_DIR}")
except Exception as e:
    logger.error(f"환경 감지 중 오류 발생: {e}", extra={
        "errorType": "EnvironmentDetectionError",
        "error_message": str(e)
    })
    raise HTTPException(status_code=500, detail="환경 감지 중 오류 발생") from e

# 저장 디렉토리 설정
UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_DIR", "storage/input_video")
CONVERT_MP3_DIR = BASE_DIR / os.getenv("CONVERT_MP3_DIR", "storage/convert_mp3")
CONVERT_TTS_DIR = BASE_DIR / os.getenv("CONVERT_TTS_DIR", "storage/convert_tts")
SCRIPTS_DIR = BASE_DIR / os.getenv("SCRIPTS_DIR", "storage/scripts")
LOGS_DIR = BASE_DIR / os.getenv("LOGS_DIR", "logs") # logs 디렉토리 추가

# 디렉토리 존재 여부 확인 및 생성
try:
    for directory in [UPLOAD_DIR, CONVERT_MP3_DIR, CONVERT_TTS_DIR, SCRIPTS_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"디렉토리가 준비되었습니다: {directory}")
        logger.debug(f"생성된 디렉토리 경로: {directory}")
except Exception as e:
    logger.error(f"디렉토리 생성 실패: {e}", extra={
        "errorType": "DirectoryCreationError",
        "error_message": str(e)
    })
    raise HTTPException(status_code=500, detail="디렉토리 생성 실패") from e