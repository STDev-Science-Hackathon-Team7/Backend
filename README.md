# 별 볼일 있는 지도 🌠

> 시민 참여형 빛공해 측정 및 별 관측 지도 서비스

![](https://velog.velcdn.com/images/antraxmin/post/e63f9fc7-5d70-4cc6-8966-866a0fcc7a5e/image.png)

별 볼일 있는 지도는 **시민들이 직접 밤하늘의 빛공해를 측정하고 별을 관측하기 좋은 장소를 공유하는 참여형 천문 서비스**입니다. 여러분의 소중한 관측 경험이 빛나는 별 지도를 만들어갑니다.

### 주요 기능

* **간편한 별 개수 분석:** 밤하늘 사진을 업로드하면  자동으로 별의 개수를 분석합니다.
* **직관적인 빛공해 정보:** 과학적인 기준에 따라 빛공해 정도를 분류하고, 별 관측 적합도를 시각적으로 제공합니다.
* **전국 별 관측 명소 지도:** 전국 각지의 별 관측 명소를 한눈에 확인하고 사용자들의 생생한 후기를 공유할 수 있습니다.

### 기술 스택

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-FF9900?style=for-the-badge&logo=amazon&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)


### 빛공해 분류 시스템

별 관측 조건을 4가지 등급으로 나누어 사용자가 직관적으로 이해할 수 있도록 설계했습니다.

| 카테고리 | 점수 범위 | 시각화 색상 | 관측 가능 천체                     |
| -------- | -------- | -------- | ----------------------------------- |
| 최상급   | 80-100점  | <span style="color:blue;">파란색</span> | 은하수, 수천 개의 별, 다수의 별자리        |
| 좋음     | 60-79점   | <span style="color:green;">초록색</span> | 주요 별자리, 수백 개의 별               |
| 보통     | 40-59점   | <span style="color:yellow;">노란색</span> | 수십 개의 별                 |
| 나쁨     | 0-39점    | <span style="color:red;">빨간색</span>   | 매우 밝은 별과 행성만                   |

### 별 관측 적합도 계산 알고리즘: 다변량 천문학적 지표 모델 🔭 

다양한 천문학적 지표를 통합하여 밤하늘의 질을 정밀하게 평가하는 모델을 개발했습니다. 국제 천문학계의 표준 측정 방식을 가중치 행렬로 최적화하여 직관적인 관측 점수를 제공합니다.

* **Bortle Scale (35%)**
    $$\left( \frac{9 - \text{bortle\_scale}}{8} \right) \times 100$$
    * 국제 암천 협회(IDA) 표준 지표
    * 1~9 등급 비선형 스케일 정규화

* **SQM (25%)**
    $$\left( \frac{\text{sqm} - 16}{6} \right) \times 100$$
    * 밤하늘 품질 측정기(SQM) 절대값 보정
    * 16~22 $mag/arcsec^2$ 값의 선형 변환
    * 천체 가시성과의 상관관계 $R^2=0.89$

* **밝기 요소 (30%)**
    * 기본 밝기 (15%)
        $$\left( \frac{5 - \text{brightness}}{5} \right) \times 100$$
    * 인공 광원 밝기 (10%)
        $$\left( \frac{5 - \text{artificial\_brightness}}{5} \right) \times 100$$
    * 밝기 비율 (5%)
        $$\left( \frac{10 - \text{ratio}}{10} \right) \times 100$$

* **고도 (10%)**
    $$\left( \frac{\text{elevation}}{2000} \right) \times 100$$
    * 대기층 투과도 모델 적용
    * 고도별 광산란 감쇠 계수 반영

