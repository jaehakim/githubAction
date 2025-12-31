import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. 텔레그램 설정 (GitHub Secrets)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram_photo(photo_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as f:
        files = {'photo': f}
        data = {'chat_id': CHAT_ID, 'caption': '📋 나라장터 발주목록 현황'}
        requests.post(url, files=files, data=data)

# 2. 브라우저 설정
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080") # 표가 넓어서 크게 설정
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# 관공서 사이트 차단 방지용 User-Agent
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20) # 최대 20초 대기

try:
    print("1. 나라장터 접속 중...")
    driver.get("https://www.g2b.go.kr/index.jsp")
    
    # 3. 메뉴 이동 (메인화면 -> 발주 -> 발주목록)
    # 나라장터는 프레임이 많아 XPATH로 찾는게 가장 정확합니다.
    print("2. [발주] 메뉴 클릭")
    # 상단 메인 메뉴 '발주' 찾기 (ID나 텍스트로 접근)
    order_menu = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "발주")))
    order_menu.click()

    print("3. [발주목록] 메뉴 클릭")
    # 좌측 사이드바 혹은 상단 서브메뉴에서 '발주목록' 찾기
    # (페이지 로딩 기다림)
    order_list_menu = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "발주목록")))
    order_list_menu.click()

    # 4. 검색 조건 설정 및 클릭 (필요시)
    print("4. 목록 로딩 대기 및 검색")
    
    # 팁: 나라장터는 프레임(iframe) 안에 내용이 있을 수 있습니다.
    # 만약 요소를 못 찾는다면 driver.switch_to.frame('frame_name')이 필요할 수 있습니다.
    # 여기서는 검색 버튼을 찾아 누릅니다. (검색버튼 클래스명이나 텍스트로 찾기)
    search_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'검색')]/.."))) 
    search_btn.click()
    
    # 결과 테이블이 뜰 때까지 잠시 대기 (명시적 대기 권장)
    time.sleep(5) 

    # 5. 캡처
    print("5. 화면 캡처")
    screenshot_path = "g2b_result.png"
    
    # 전체 화면 캡처
    driver.save_screenshot(screenshot_path)
    
    # 6. 전송
    send_telegram_photo(screenshot_path)
    print("✅ 전송 완료")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    # 오류 났을 때 화면도 캡처해서 보내면 디버깅에 좋습니다
    driver.save_screenshot("error.png")
    send_telegram_photo("error.png")

finally:
    driver.quit()
