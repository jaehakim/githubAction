import os
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Discord Webhook 설정 (GitHub Secrets)
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_GOLD_PRICE_WEBHOOK_URL')

# GitHub Actions 환경 정보
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY', '')
GITHUB_RUN_ID = os.environ.get('GITHUB_RUN_ID', '')
GITHUB_SERVER = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')
GITHUB_ACTOR = os.environ.get('GITHUB_ACTOR', '')

# 캡처 대상 사이트
SITES = [
    {
        'name': '네이버 금시세',
        'url': 'https://search.naver.com/search.naver?query=%EA%B8%88%EC%8B%9C%EC%84%B8',
        'file': 'gold_naver.png',
        'keywords': ['금', '원/g', '매매기준', '살 때', '팔 때', '국제금', '전일대비'],
    },
    {
        'name': '다음 금시세',
        'url': 'https://search.daum.net/search?q=%EA%B8%88%EC%8B%9C%EC%84%B8',
        'file': 'gold_daum.png',
        'keywords': ['금', '원/g', '살 때', '팔 때', '국제금', '전일대비', '상승', '하락'],
    },
]


def send_discord_message(content):
    """Discord 텍스트 메시지 전송"""
    data = {'content': content}
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code in (200, 204):
        print("Discord 텍스트 전송 성공")
    else:
        print("Discord 텍스트 전송 실패:", response.status_code, response.text)


def send_discord_file(file_path, message=""):
    """Discord 파일(이미지) 전송"""
    data = {}
    if message:
        data['content'] = message
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f, 'image/png')}
        response = requests.post(DISCORD_WEBHOOK_URL, data=data, files=files)
    if response.status_code in (200, 204):
        print(f"Discord 파일 전송 성공: {file_path}")
    else:
        print(f"Discord 파일 전송 실패: {response.status_code} {response.text}")


def extract_gold_text(driver, keywords):
    """페이지 body에서 금시세 관련 텍스트 추출"""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = body_text.split('\n')
        gold_lines = []
        for line in lines:
            line = line.strip()
            if line and any(kw in line for kw in keywords):
                gold_lines.append(line)
        if gold_lines:
            return '\n'.join(gold_lines[:15])
    except Exception as e:
        print(f"텍스트 추출 오류: {e}")
    return None


def build_github_info():
    """GitHub Actions 실행 정보"""
    if not GITHUB_REPO:
        return ""
    run_url = f"{GITHUB_SERVER}/{GITHUB_REPO}/actions/runs/{GITHUB_RUN_ID}"
    repo_url = f"{GITHUB_SERVER}/{GITHUB_REPO}"
    return (
        f"\n{'─' * 35}\n"
        f"📂 Repo: {repo_url}\n"
        f"▶️ Run: {run_url}\n"
        f"👤 Actor: {GITHUB_ACTOR}"
    )


def create_driver():
    """헤드리스 Chrome 드라이버 생성"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    github_info = build_github_info()
    driver = create_driver()
    wait = WebDriverWait(driver, 15)

    results = []

    try:
        for site in SITES:
            print(f"\n{'='*40}")
            print(f"[{site['name']}] 접속: {site['url']}")
            driver.get(site['url'])
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5)  # JS 렌더링 대기

            # 텍스트 추출
            price_text = extract_gold_text(driver, site['keywords'])

            # 스크린샷 캡처
            driver.save_screenshot(site['file'])
            print(f"[{site['name']}] 캡처 완료: {site['file']}")

            results.append({
                'name': site['name'],
                'file': site['file'],
                'text': price_text or '(시세 텍스트 추출 실패 - 캡처 이미지 확인)',
            })

    except Exception as e:
        print(f"❌ 오류: {e}")
        driver.save_screenshot("error.png")
        send_discord_message(f"❌ 금시세 캡처 오류\n```{e}```{github_info}")
        return
    finally:
        driver.quit()

    # Discord 전송
    # 1) 텍스트 메시지
    msg_parts = [f"📊 **금시세** ({now})"]
    for r in results:
        msg_parts.append(f"\n**▸ {r['name']}**\n```\n{r['text']}\n```")
    msg_parts.append(f"\n{github_info}")
    send_discord_message('\n'.join(msg_parts))

    # 2) 캡처 이미지
    time.sleep(1)  # Discord rate limit 방지
    for r in results:
        send_discord_file(r['file'], f"📸 {r['name']} 캡처 ({now})")
        time.sleep(1)

    print("\n✅ 모든 전송 완료")


if __name__ == "__main__":
    main()
