import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys # 키보드 입력을 위한 모듈 추가

# 1. 텔레그램 설정 (GitHub Secrets)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram_photo(photo_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as f:
        files = {'photo': f}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        requests.post(url, files=files, data=data)

# 2. 브라우저 설정
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 30) # 대기 시간을 30초로 늘림

try:
    print("1. 나라장터 접속 중...")
    driver.get("https://www.g2b.go.kr/index.jsp")
    
    print("2. [발주] 메뉴 클릭")
    order_menu = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "발주")))
    order_menu.click()

    print("3. [발주목록] 메뉴 클릭")
    order_list_menu = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "발주목록")))
    order_list_menu.click()
    
    print("4. 목록 로딩 및 검색 버튼 클릭")
    # 이미지_0에서 확인된 파란색 검색 버튼 XPATH
    search_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'btn_blue') and contains(text(), '검색')]"))) 
    search_btn.click()
    time.sleep(3) # 팝업 뜨는 대기 시간

    print("5. 검색어 입력 및 검색 실행 (RFID)")
    # 이미지_1에서 확인된 검색어 입력 필드 및 돋보기 아이콘 XPATH
    # 1) 검색어 입력 필드 찾기 및 'RFID' 입력
    search_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='검색어를 입력해 주세요.']")))
    search_input.click()
    search_input.clear()
    search_input.send_keys("RFID")
    time.sleep(1) # 입력 대기

    # 2) 돋보기 모양 검색 실행 버튼 클릭
    # 입력 필드 옆의 돋보기 아이콘을 찾아 클릭합니다. 실제 사이트 구조에 따라 XPATH는 달라질 수 있습니다.
    # 여기서는 입력 필드를 감싸는 부모 요소 내의 아이콘을 찾는 일반적인 방법을 사용합니다.
    # 만약 이 XPATH가 작동하지 않으면, 실제 사이트 개발자 도구(F12)를 통해 정확한 경로를 확인해야 합니다.
    search_execute_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='검색어를 입력해 주세요.']/following-sibling::*[contains(@class, 'search')]"))) # 예시 XPATH
    search_execute_btn.click()

    print("6. 검색 결과 로딩 대기")
    time.sleep(5) # 검색 결과 로딩 대기

    print("7. 화면 캡처")
    screenshot_path = "g2b_rfid_result.png"
    driver.save_screenshot(screenshot_path)
    
    print("8. 텔레그램 전송")
    send_telegram_photo(screenshot_path, '📋 나라장터 발주목록 (RFID 검색 결과)')
    print("✅ 전송 완료")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    driver.save_screenshot("error.png")
    send_telegram_photo("error.png", f"❌ 오류 발생: {e}")

finally:
    driver.quit()
