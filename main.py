import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 1. 텔레그램 설정 (GitHub Secrets에서 가져옴)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram_photo(photo_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    
    with open(photo_path, 'rb') as f:
        # 텔레그램 API에 이미지와 채팅방 ID 전송
        files = {'photo': f}
        data = {'chat_id': CHAT_ID, 'caption': '🚀 검색 결과 캡처 도착!'}
        response = requests.post(url, files=files, data=data)
        
    if response.status_code == 200:
        print("전송 성공")
    else:
        print("전송 실패:", response.text)

# 2. 브라우저 설정 (헤드리스 모드)
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
# 리눅스 환경에서 샌드박스 문제 방지
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

try:
    # 3. 사이트 접속 및 캡처 (예: 네이버 증권)
    driver.get("https://finance.naver.com/")
    driver.implicitly_wait(3) # 로딩 대기
    
    screenshot_path = "result.png"
    driver.save_screenshot(screenshot_path)
    print("스크린샷 저장 완료")

    # 4. 텔레그램 전송
    send_telegram_photo(screenshot_path)

finally:
    driver.quit()
