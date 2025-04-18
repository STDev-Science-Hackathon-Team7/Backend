import cv2
import os
from datetime import datetime
from fastapi import logger
import numpy as np
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
            Dict: 별 개수 및 관련 정보 
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

            # 다양한 밝기 조건에서도 별을 감지할 수 있도록
            thresh = cv2.adaptiveThreshold(
                blurred,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                15,
                -2
            )

             # 아주 밝은 별을 감지하기 위한 고정 임계값을 추가로 적용 
            _, bright_stars = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)

            # 두 임계값 결과를 결합
            combined = cv2.bitwise_or(thresh, bright_stars)

            # 노이즈 제거
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            opening = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)

            # 연결된 컴포넌트 찾아서 별 감지
            contours, _ = cv2.findContours(
                opening,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            min_area = 3  
            max_area = 150  
            min_circularity = 0.3  

            stars = []
            for contour in contours:
                area = cv2.contourArea(contour)

                if min_area <= area <= max_area:
                    perimeter = cv2.arcLength(contour, True)        # 원형도 계산
                    if perimeter == 0:
                        continue
                    circularity = 4 * np.pi * area / (perimeter * perimeter)

                    if circularity >= min_circularity:
                        M = cv2.moments(contour)        # 무게중심 계산
                        if M["m00"] == 0:
                            continue

                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])

                        stars.append((cx, cy))              # 유효한 별의 좌표를  저장

            processing_time = (datetime.now() - start_time).total_seconds()
            star_count = len(stars)
            star_category = self.determine_star_count_category(star_count)
            ui_message = self.get_star_count_message(star_count, star_category)

            return {
                "star_count": star_count,
                "star_category": star_category,
                "ui_message": ui_message
            }

        except FileNotFoundError as e:
            logger.error(f"파일 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"별 카운팅 에러 : {str(e)}")
            raise
    
    def determine_star_count_category(self, star_count: int) -> str:
        """
        별 개수에 따른 관측 카테고리를 결정하는 함수

        Args:
            star_count: 감지된 별의 개수

        Returns:
            str: 관측 카테고리 (최상급-레벨4/좋음-레벨3/보통-레벨2/나쁨-레벨1)
        """
        # 기준점은 추후 변경 가능
        if star_count >= 500:
            return "레벨 4"
        elif star_count >= 100:
            return "레벨 3"
        elif star_count >= 15:
            return "레벨 2"
        else:
            return "레벨 1"
    
    def get_star_count_message(self, star_count: int, category: str) -> str:
        """
        사용자에게 표시할 별 카운팅 결과 메시지 생성

        Args:
            star_count: 감지된 별의 개수
            category: 별 관측 카테고리

        Returns:
            str: 메시지
        """
        if category == "레벨 4":
            return f"오늘 {star_count}개의 별이 관측되었어요. 은하수도 선명하게 관측할 수 있는 최상의 조건이에요."
        elif category == "레벨 3":
            return f"오늘 {star_count}개의 별이 관측되었어요. 많은 별자리를 볼 수 있는 좋은 관측 조건이에요."
        elif category == "레벨 2":
            return f"오늘 {star_count}개의 별이 관측되었어요. 주요 별자리를 볼 수 있는 보통 수준의 밤하늘이에요."
        else:
            return f"오늘 {star_count}개의 별이 관측되었어요. 도시 불빛으로 인해 별이 잘 보이지 않는 조건이에요."

star_counter = StarCounter()

# 프론트에서 받는 응답값 형식

# {
#   "star_count": 15,
#   "star_category": "좋음",
#   "ui_message": "오늘 15개의 별이 관측되었어요. 주요 별자리를 볼 수 있는 보통 수준의 밤하늘이에요."
# }