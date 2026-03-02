import os
import re
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
        'name': '네이버',
        'url': 'https://search.naver.com/search.naver?query=%EA%B8%88%EC%8B%9C%EC%84%B8',
        'file': 'gold_naver.png',
    },
    {
        'name': '다음',
        'url': 'https://search.daum.net/search?q=%EA%B8%88%EC%8B%9C%EC%84%B8',
        'file': 'gold_daum.png',
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


def extract_gold_summary(driver, site_name):
    """페이지에서 금시세 핵심 데이터만 추출"""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = body_text.split('\n')
        lines = [l.strip() for l in lines if l.strip()]
    except Exception as e:
        print(f"텍스트 추출 오류: {e}")
        return None

    # 가격 패턴: 숫자+콤마+소수점 (예: 242,096.67)
    price_re = re.compile(r'[\d,]+(?:\.\d+)?')

    result = {}

    for i, line in enumerate(lines):
        # 매매기준가
        if '매매' in line and '기준' in line:
            prices = price_re.findall(line)
            if prices:
                result['매매기준가'] = prices[0] + '원/g'
            elif i + 1 < len(lines):
                prices = price_re.findall(lines[i + 1])
                if prices:
                    result['매매기준가'] = prices[0] + '원/g'

        # 살 때
        if '살 때' in line or '살때' in line:
            prices = price_re.findall(line)
            if prices:
                result['살 때'] = prices[0] + '원'
            elif i + 1 < len(lines):
                prices = price_re.findall(lines[i + 1])
                if prices:
                    result['살 때'] = prices[0] + '원'

        # 팔 때
        if '팔 때' in line or '팔때' in line:
            prices = price_re.findall(line)
            if prices:
                result['팔 때'] = prices[0] + '원'
            elif i + 1 < len(lines):
                prices = price_re.findall(lines[i + 1])
                if prices:
                    result['팔 때'] = prices[0] + '원'

        # 전일대비
        if '전일대비' in line or '전일 대비' in line:
            prices = price_re.findall(line)
            direction = ''
            if '상승' in line or '+' in line or '▲' in line:
                direction = '▲ '
            elif '하락' in line or '-' in line or '▼' in line:
                direction = '▼ '
            if prices:
                result['전일대비'] = direction + prices[0] + '원'

        # 국제금 (달러)
        if '국제금' in line or '달러' in line or '$/온스' in line:
            prices = price_re.findall(line)
            if prices:
                # 달러 가격은 보통 1,000 이상의 값
                for p in prices:
                    val = float(p.replace(',', ''))
                    if val > 500:
                        result['국제금'] = p + '$/oz'
                        break

        # 1돈 가격
        if '1돈' in line or '한돈' in line or '3.75g' in line:
            prices = price_re.findall(line)
            if prices:
                for p in prices:
                    val = float(p.replace(',', ''))
                    if val > 100000:
                        result['1돈(3.75g)'] = p + '원'
                        break

    # 변동률 추출 (별도)
    pct_match = re.search(r'([+-]?\d+\.\d+)\s*%', body_text)
    if pct_match and '전일대비' in result:
        result['전일대비'] += f' ({pct_match.group(1)}%)'
    elif pct_match:
        direction = '▲ ' if not pct_match.group(1).startswith('-') else '▼ '
        result['변동률'] = direction + pct_match.group(1) + '%'

    return result


def format_summary(site_name, data):
    """추출된 데이터를 깔끔한 텍스트로 포맷"""
    if not data:
        return f"**{site_name}** : 추출 실패 (캡처 이미지 확인)"

    lines = [f"**[ {site_name} ]**"]

    # 출력 순서 지정
    order = ['매매기준가', '전일대비', '변동률', '살 때', '팔 때', '1돈(3.75g)', '국제금']
    labels = {
        '매매기준가': '기준가',
        '전일대비': '전일대비',
        '변동률': '변동률',
        '살 때': '살 때',
        '팔 때': '팔 때',
        '1돈(3.75g)': '1돈(3.75g)',
        '국제금': '국제금',
    }

    for key in order:
        if key in data:
            lines.append(f"  {labels[key]:　<8} {data[key]}")

    return '\n'.join(lines)


def build_github_info():
    """GitHub Actions 실행 정보"""
    if not GITHUB_REPO:
        return ""
    run_url = f"{GITHUB_SERVER}/{GITHUB_REPO}/actions/runs/{GITHUB_RUN_ID}"
    return f"\n─────────────────────\n▶ {run_url}"


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

            # 핵심 데이터 추출
            data = extract_gold_summary(driver, site['name'])
            summary = format_summary(site['name'], data)
            print(summary)

            # 스크린샷 캡처
            driver.save_screenshot(site['file'])
            print(f"[{site['name']}] 캡처 완료: {site['file']}")

            results.append({
                'name': site['name'],
                'file': site['file'],
                'summary': summary,
            })

    except Exception as e:
        print(f"오류: {e}")
        driver.save_screenshot("error.png")
        send_discord_message(f"금시세 캡처 오류\n```{e}```{github_info}")
        return
    finally:
        driver.quit()

    # Discord 전송
    # 1) 핵심 시세 텍스트
    msg_parts = [f"**금시세 ({now})**\n"]
    for r in results:
        msg_parts.append(r['summary'])
    msg_parts.append(github_info)
    send_discord_message('\n'.join(msg_parts))

    # 2) 캡처 이미지
    time.sleep(1)
    for r in results:
        send_discord_file(r['file'])
        time.sleep(1)

    print("\n모든 전송 완료")


if __name__ == "__main__":
    main()
