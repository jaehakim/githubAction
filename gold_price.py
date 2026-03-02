import os
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. 텔레그램 설정 (GitHub Secrets)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram_photo(photo_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as f:
        files = {'photo': f}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data)
    if response.status_code == 200:
        print("전송 성공")
    else:
        print("전송 실패:", response.text)

# 2. 브라우저 설정 (헤드리스 모드)
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

try:
    # 3. 한국금거래소 접속
    print("1. 한국금거래소 접속 중...")
    driver.get("https://www.koreagoldx.co.kr/main/main.do")

    # 4. 페이지 로딩 대기
    print("2. 페이지 로딩 대기...")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    driver.implicitly_wait(3)

    # 5. 스크린샷 캡처
    print("3. 화면 캡처")
    screenshot_path = "gold_price.png"
    driver.save_screenshot(screenshot_path)
    print("스크린샷 저장 완료")

    # 6. 텔레그램 전송
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print("4. 텔레그램 전송")
    send_telegram_photo(screenshot_path, f'📊 금시세 ({now})\n출처: 한국금거래소')
    print("✅ 전송 완료")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    driver.save_screenshot("error.png")
    send_telegram_photo("error.png", f"❌ 금시세 캡처 오류: {e}")

finally:
    driver.quit()
