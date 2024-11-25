# utils/calculate_presentation_score.py

from .tts import TTS
from .stt import STT
from .correct_text_with_llm import correct_text_with_llm
from .calculate_audio_duration import calculate_audio_duration
from .count_words import count_words
from .calculate_speed import calculate_speed
from .adjust_audio_length import adjust_audio_length
from .analyze_low_accuracy import analyze_low_accuracy
from .compare_audio_similarity import compare_audio_similarity
from .analyze_pronunciation_accuracy import analyze_pronunciation_accuracy
from typing import Optional, Dict, Any
import logging

def calculate_presentation_score(audio_file_path: str, script_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    프레젠테이션 음성을 분석하여 점수를 계산합니다.

    Args:
        audio_file_path (str): 입력 오디오 파일 경로.
        script_text (str, optional): 기준 텍스트 (사용자가 제공한 스크립트). 제공되지 않으면 STT 결과를 사용.

    Returns:
        dict: 분석 결과를 포함한 점수 데이터. (오디오 유사도, 말하기 속도, 발음 정확도)
        None: 처리 실패 시.
    """
    try:
        # --- 음성 정보 ---
        # Step 1: STT(음성을 텍스트로 변환)
        stt_text = STT(audio_file_path)
        if not stt_text:
            logging.error("STT 변환에 실패했습니다.")
            return None
        logging.debug("STT 변환된 텍스트:\n%s", stt_text)  # 필요 시 주석 해제

        # Step 2: 기준 텍스트 확인
        if script_text:
            # 사용자가 제공한 스크립트를 기준으로 사용
            logging.info("사용자가 제공한 스크립트를 사용합니다.")
        else:
            # 기준 스크립트가 없는 경우, LLM을 통해 STT 결과를 보정하여 사용
            logging.info("스크립트가 제공되지 않았습니다. LLM으로 텍스트를 보정합니다.")
            script_text = correct_text_with_llm(stt_text)
            logging.debug("LLM으로 보정된 텍스트:\n%s", script_text)

        print("— 음성 정보 —")

        # Step 3: WPM 계산 (decoded_text 기반)
        audio_duration = calculate_audio_duration(audio_file_path)
        word_count = count_words(stt_text)
        user_speed = calculate_speed(audio_file_path, stt_text)
        print(f"오디오 길이 (초): {audio_duration:.2f}")
        print(f"텍스트 단어 수: {word_count}")
        print(f"사용자 발표 WPM: {user_speed:.2f}")

        # Step 4: TTS 속도 설정
        average_wpm = 100  # 평균 말하기 속도
        tts_speed_ratio = user_speed / average_wpm  # TTS 속도 비율 계산
        tts_speed_ratio = max(0.5, min(tts_speed_ratio, 4.0))  # 속도 제한 적용
        print(f"TTS 속도 설정: {tts_speed_ratio:.2f}")

        # TTS 생성
        tts_file_path = TTS(script_text, speed=tts_speed_ratio)
        if not tts_file_path:
            logging.error("TTS 변환에 실패했습니다.")
            return None

        # TTS 속도 (WPM) 계산
        tts_wpm = tts_speed_ratio * average_wpm
        print(f"TTS WPM: {tts_wpm:.2f} WPM")

        # Step 5: TTS와 사용자 음성 길이 동기화
        adjust_audio_length(tts_file_path, audio_duration)

        # --- 발음 정확도 계산 ---
        print("\n— 구간별 발음 정확도 계산 —")
        low_accuracies, wpms, average_accuracy = analyze_low_accuracy(audio_file_path, script_text, chunk_size=60)

        for time_str, accuracy in low_accuracies:
            print(f"{time_str} 구간의 발음 정확도: {accuracy:.2f}")

        print("\n- 구간별 WPM -")
        for time_str, wpm in wpms:
            print(f"{time_str}구간의 WPM: {wpm:.2f}")

        # Step 6: 오디오 유사도 계산
        audio_similarity = compare_audio_similarity(audio_file_path, tts_file_path)
        if audio_similarity is None:
            logging.error("오디오 유사도 비교에 실패했습니다.")
            return None

        # Step 7: 발음 정확도 계산
        pronunciation_accuracy = analyze_pronunciation_accuracy(stt_text, script_text)
        if pronunciation_accuracy is None:
            logging.error("대본 텍스트와 일치도 분석에 실패했습니다.")
            return None

        # --- pronunciation_scores 및 wpm_scores 추가 ---
        pronunciation_scores = [
            {"time_segment": time_str, "accuracy": accuracy}
            for time_str, accuracy in low_accuracies
        ]
        wpm_scores = [
            {"time_segment": time_str, "wpm": wpm}
            for time_str, wpm in wpms
        ]

        # 최종 결과 반환
        return {
            "audio_similarity": audio_similarity,
            "original_speed": user_speed,
            "tts_speed": tts_wpm,  # 실제 WPM으로 환산
            "average_accuracy": average_accuracy,
            "pronunciation_accuracy": pronunciation_accuracy,
            "tts_file_path": tts_file_path,  # TTS 파일 경로 추가
            "pronunciation_scores": pronunciation_scores,  # 추가
            "wpm_scores": wpm_scores  # 추가
        }
    
    except Exception as e:
        logging.error(f"발표 점수 계산 중 오류 발생: {e}")
        return None