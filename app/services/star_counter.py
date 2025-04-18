import cv2
import os
from datetime import datetime
from fastapi import logger
from app.config import settings

class StarCounter:
    """밤하늘 사진에서 별의 개수를 세는 OpenCV 기반 알고리즘"""

    def __init__(self):
        cv2.setNumThreads(16)       # 멀티스레딩 활성화 

        self.debug_dir = os.path.join(settings.UPLOAD_DIR, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)

    def count_stars(self, image_path: str, debug: bool = False):
        """
        밤하늘 사진에서 별 개수를 세는 함수

        Args:
            image_path: 이미지 파일 경로
            debug: 디버그 모드 활성화 여부 (추후 구현해야함)

        Returns:
            Dict: 별 개수 및 관련 정보 (추후 구현해야 함, 현재는 기본 딕셔너리 반환)
        """
        try:
            start_time = datetime.now()

            original_img = cv2.imread(image_path)
            if original_img is None:
                raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {image_path}")

            height, width = original_img.shape[:2]      # 이미지 크기 확인 
            max_dimension = 1920  

            if max(height, width) > max_dimension:
                scale = max_dimension / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                original_img = cv2.resize(original_img, (new_width, new_height))
                logger.info(f"이미지 리사이즈: {width}x{height} -> {new_width}x{new_height}")

            gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)       # 그레이스케일 변환
            blurred = cv2.GaussianBlur(gray, (11, 11), 0)                   # 가우시안 블러로 노이즈 제거
            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "star_count": 0,  
                "processing_time": processing_time,
                "preprocessed_image_shape": blurred.shape if blurred is not None else None
            }

        except FileNotFoundError as e:
            logger.error(f"파일 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"별 카운팅 (전처리) 에러 : {str(e)}")
            raise

star_counter = StarCounter()