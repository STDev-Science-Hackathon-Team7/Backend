import cv2
import os
from datetime import datetime
from fastapi import logger
import numpy as np
from app.config import settings

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StarCounter:
    """밤하늘 사진에서 별의 개수를 세는 OpenCV 기반 알고리즘"""

    def __init__(self):
        cv2.setNumThreads(16)
        self.debug_dir = os.path.join(settings.UPLOAD_DIR, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)

    def is_night_sky(self, img):
        """
        이미지가 밤하늘인지 확인하는 함수
        
        Args:
            img: 분석할 이미지
            
        Returns:
            bool: 밤하늘 여부
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        avg_brightness = np.mean(hsv[:,:,2])
        
        dark_pixels = np.sum(hsv[:,:,2] < 50) / (img.shape[0] * img.shape[1])
        
        blue_mask = cv2.inRange(hsv, (100, 0, 0), (140, 255, 100))
        blue_pixels = np.sum(blue_mask > 0) / (img.shape[0] * img.shape[1])
        
        is_night = (avg_brightness < 100 and dark_pixels > 0.6)
        
        
        return is_night

    def filter_light_sources(self, img, stars):
        """
        별이 아닌 인공 광원을 필터링하는 함수
        
        Args:
            img: 원본 이미지
            stars: 감지된 별 좌표 리스트
            
        Returns:
            list: 필터링된 별 좌표 리스트
        """
        filtered_stars = []
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        for x, y in stars:
            if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
                roi_size = 5
                x1, y1 = max(0, x - roi_size), max(0, y - roi_size)
                x2, y2 = min(img.shape[1], x + roi_size), min(img.shape[0], y + roi_size)
                
                if x1 >= x2 or y1 >= y2:
                    continue
                
                roi = img[y1:y2, x1:x2]
                hsv_roi = hsv[y1:y2, x1:x2]
                
                gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                center_brightness = gray_roi[roi_size, roi_size] if roi_size < gray_roi.shape[0] and roi_size < gray_roi.shape[1] else 0
                avg_edge_brightness = np.mean(np.concatenate([
                    gray_roi[0,:], gray_roi[-1,:], gray_roi[:,0], gray_roi[:,-1]
                ]))
                
                brightness_pattern = center_brightness > avg_edge_brightness * 1.3
                
                b, g, r = np.mean(roi[:,:,0]), np.mean(roi[:,:,1]), np.mean(roi[:,:,2])
                color_ratio = max(b, g, r) / (min(b, g, r) + 0.01)
                
                color_balance = color_ratio < 3.0
                
                if brightness_pattern and color_balance:
                    filtered_stars.append((x, y))
        
        return filtered_stars

    def count_stars(self, image_path: str, debug: bool = False):
        """
        밤하늘 사진에서 별 개수를 세는 함수

        Args:
            image_path: 이미지 파일 경로
            debug: 디버그 모드 활성화 여부

        Returns:
            Dict: 별 개수 및 관련 정보 
        """
        try:
            start_time = datetime.now()

            original_img = cv2.imread(image_path)
            if original_img is None:
                raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {image_path}")

            height, width = original_img.shape[:2]
            max_dimension = 1920  

            if max(height, width) > max_dimension:
                scale = max_dimension / max(height, width)
                new_width = int(width * scale)
                new_height = int(height * scale)
                original_img = cv2.resize(original_img, (new_width, new_height))

            # # 밤하늘 감지 필터 적용
            # if not self.is_night_sky(original_img):
            #     return {
            #         "star_count": 0,
            #         "star_category": "1",  # 가장 낮은 등급
            #         "ui_message": "이 이미지는 밤하늘이 아니거나 구름이 많아 별을 관측하기 어려운 조건입니다."
            #     }

            gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
            
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)

            thresh = cv2.adaptiveThreshold(
                blurred,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                13,  
                -3  
            )

            _, bright_stars = cv2.threshold(blurred, 210, 255, cv2.THRESH_BINARY)
            combined = cv2.bitwise_or(thresh, bright_stars)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            opening = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(
                opening,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            min_area = 4       
            max_area = 100     
            min_circularity = 0.5 

            stars = []
            for contour in contours:
                area = cv2.contourArea(contour)

                if min_area <= area <= max_area:
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter == 0:
                        continue
                    
                    circularity = 4 * np.pi * area / (perimeter * perimeter)

                    if circularity >= min_circularity:
                        M = cv2.moments(contour)
                        if M["m00"] == 0:
                            continue

                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])

                        stars.append((cx, cy))

            # 별이 아닌 광원 필터링
            filtered_stars = self.filter_light_sources(original_img, stars)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            star_count = len(filtered_stars)
            
            if debug:
                debug_img = original_img.copy()
                for x, y in filtered_stars:
                    cv2.circle(debug_img, (x, y), 5, (0, 255, 0), 1)
                
                debug_path = os.path.join(self.debug_dir, f"debug_{os.path.basename(image_path)}")
                cv2.imwrite(debug_path, debug_img)
                logger.info(f"디버그 이미지 저장됨: {debug_path}")

            star_category = self.determine_star_count_category(star_count)
            ui_message = self.get_star_count_message(star_count, star_category)

            logger.info(f"별 카운팅 완료: {star_count}개 감지, 카테고리: {star_category}, 처리 시간: {processing_time:.2f}초")

            return {
                "star_count": star_count,
                "star_category": star_category,
                "ui_message": ui_message
            }

        except FileNotFoundError as e:
            logger.error(f"파일 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"별 카운팅 에러: {str(e)}")
            raise
    
    def determine_star_count_category(self, star_count: int) -> str:
        """별 개수에 따른 관측 카테고리 결정"""
        if star_count >= 300:
            return "4" 
        elif star_count >= 80:
            return "3"  
        elif star_count >= 10:
            return "2"  
        else:
            return "1" 
    
    def get_star_count_message(self, star_count: int, category: str) -> str:
        """사용자에게 표시할 별 카운팅 결과 메시지 생성"""
        if category == "4":
            return f"오늘 {star_count}개의 별이 관측되었어요. 은하수도 선명하게 관측할 수 있는 최상의 조건이에요."
        elif category == "3":
            return f"오늘 {star_count}개의 별이 관측되었어요. 많은 별자리를 볼 수 있는 좋은 관측 조건이에요."
        elif category == "2":
            return f"오늘 {star_count}개의 별이 관측되었어요. 주요 별자리를 볼 수 있는 보통 수준의 밤하늘이에요."
        else:
            if star_count == 0:
                return "별이 관측되지 않았어요. 밤하늘이 아니거나 구름이 많은 것 같습니다."
            else:
                return f"오늘 {star_count}개의 별이 관측되었어요. 도시 불빛으로 인해 별이 잘 보이지 않는 조건이에요."

star_counter = StarCounter()