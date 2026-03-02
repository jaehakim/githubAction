import os
import time
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

# GitHub Actions 환경 정보
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY', '')
GITHUB_RUN_ID = os.environ.get('GITHUB_RUN_ID', '')
GITHUB_SERVER = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')
GITHUB_ACTOR = os.environ.get('GITHUB_ACTOR', '')


def send_telegram_message(text):
    """텔레그램 텍스트 메시지 전송"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("텍스트 전송 성공")
    else:
        print("텍스트 전송 실패:", response.text)


def send_telegram_photo(photo_path, caption):
    """텔레그램 이미지 전송"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as f:
        files = {'photo': f}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        response = requests.post(url, files=files, data=data)
    if response.status_code == 200:
        print("이미지 전송 성공")
    else:
        print("이미지 전송 실패:", response.text)


def extract_gold_prices(driver):
    """페이지에서 금시세 텍스트 추출"""
    prices = {}
    try:
        # 시세 항목들 추출 시도
        items = driver.find_elements(By.CSS_SELECTOR, ".lineup-price__item, .lineup-descbox, .main-lineup")
        if items:
            for item in items:
                text = item.text.strip()
                if text:
                    prices['raw'] = text
                    break

        # 위 방법 실패 시 전체 시세 영역 텍스트 추출
        if not prices:
            selectors = [".main-lineup", ".price-section", ".gold-price", "table"]
            for sel in selectors:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    text = el.text.strip()
                    if '금' in text or 'gold' in text.lower() or '원' in text:
                        prices['raw'] = text
                        break
                if prices:
                    break

        # 최후 수단: body에서 금시세 관련 텍스트 추출
        if not prices:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            lines = body_text.split('\n')
            gold_lines = []
            for line in lines:
                line = line.strip()
                if any(kw in line for kw in ['순금', '24K', '18K', '14K', '백금', '은시세', '매입', '매도', 'Gold']):
                    gold_lines.append(line)
            if gold_lines:
                prices['raw'] = '\n'.join(gold_lines[:20])

    except Exception as e:
        print(f"시세 추출 오류: {e}")

    return prices


def build_github_info():
    """GitHub Actions 실행 정보 텍스트 생성"""
    if not GITHUB_REPO:
        return ""

    run_url = f"{GITHUB_SERVER}/{GITHUB_REPO}/actions/runs/{GITHUB_RUN_ID}"
    repo_url = f"{GITHUB_SERVER}/{GITHUB_REPO}"

    info = (
        f"\n{'─' * 30}\n"
        f"📂 Repo: {repo_url}\n"
        f"▶️ Run: {run_url}\n"
        f"👤 Actor: {GITHUB_ACTOR}"
    )
    return info


# 2. 브라우저 설정 (헤드리스 모드)
options = Options()
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

try:
    # 3. 국제표준금거래소 접속
    print("1. 국제표준금거래소 접속 중...")
    driver.get("https://www.goodgold.co.kr/")

    # 4. 페이지 로딩 대기 (JS 렌더링 + 시세 데이터)
    print("2. 페이지 로딩 대기...")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(5)

    # 5. 금시세 텍스트 추출
    print("3. 금시세 텍스트 추출...")
    prices = extract_gold_prices(driver)

    # 6. 스크린샷 캡처
    print("4. 화면 캡처")
    screenshot_path = "gold_price.png"
    driver.save_screenshot(screenshot_path)
    print("스크린샷 저장 완료")

    # 7. 텔레그램 전송 - 텍스트 메시지
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    github_info = build_github_info()

    price_text = prices.get('raw', '시세 추출 실패 (캡처 이미지 확인)')
    message = (
        f"📊 <b>금시세</b> ({now})\n"
        f"{'━' * 25}\n"
        f"{price_text}\n"
        f"{'━' * 25}\n"
        f"출처: 국제표준금거래소 goodgold.co.kr"
        f"{github_info}"
    )

    print("5. 텔레그램 텍스트 전송")
    send_telegram_message(message)

    # 8. 텔레그램 전송 - 캡처 이미지
    print("6. 텔레그램 이미지 전송")
    send_telegram_photo(screenshot_path, f"📸 금시세 캡처 ({now})")
    print("✅ 전송 완료")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    driver.save_screenshot("error.png")
    github_info = build_github_info()
    send_telegram_message(f"❌ 금시세 캡처 오류\n{e}{github_info}")

finally:
    driver.quit()
