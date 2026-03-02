import json
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

# Discord Webhook 설정 (GitHub Secrets)
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_GOLD_PRICE_WEBHOOK_URL')

# GitHub Actions 환경 정보
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY', '')
GITHUB_RUN_ID = os.environ.get('GITHUB_RUN_ID', '')
GITHUB_SERVER = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')

# 스크린샷 캡처용 (검색결과 - 시각적 요약)
SCREENSHOT_SITES = [
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

# 텍스트 추출용 (금융 페이지 - 정확한 수치)
TEXT_SOURCES = [
    {
        'name': '네이버',
        'url': 'https://finance.naver.com/marketindex/goldDetail.nhn',
    },
    {
        'name': '다음',
        'url': 'https://finance.daum.net/domestic/exchange/COMMODITY-GOLD',
    },
]

# 가격 유효 범위 (비정상값 필터링)
VALID_RANGES = {
    '기준가':   (50_000, 1_500_000),
    '살때':     (50_000, 1_500_000),
    '팔때':     (50_000, 1_500_000),
    '전일대비': (10, 100_000),
    '국제금':   (500, 20_000),
    '1돈':      (200_000, 10_000_000),
}


def send_discord_combined(content, image_paths):
    """Discord Webhook으로 텍스트 + 이미지를 하나의 메시지로 전송"""
    payload = json.dumps({'content': content})
    files = {'payload_json': (None, payload, 'application/json')}

    open_handles = []
    for i, path in enumerate(image_paths):
        if os.path.exists(path):
            f = open(path, 'rb')
            open_handles.append(f)
            files[f'file{i}'] = (os.path.basename(path), f, 'image/png')

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, files=files)
        if response.status_code in (200, 204):
            print("Discord 전송 성공")
        else:
            print(f"Discord 전송 실패: {response.status_code} {response.text}")
    finally:
        for f in open_handles:
            f.close()


def find_price(text, min_val, max_val):
    """텍스트에서 유효 범위 내의 가격을 찾아 반환"""
    numbers = re.findall(r'\d[\d,]*(?:\.\d+)?', text)
    for n in numbers:
        try:
            val = float(n.replace(',', ''))
            if min_val <= val <= max_val:
                return n
        except ValueError:
            continue
    return None


def extract_gold_data(driver, source):
    """금융 페이지에서 금시세 핵심 데이터 추출"""
    print(f"[텍스트] {source['name']} 접속: {source['url']}")
    driver.get(source['url'])

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(5)
    except Exception as e:
        print(f"  페이지 로딩 실패: {e}")
        return {}

    body_text = driver.find_element(By.TAG_NAME, "body").text
    lines = body_text.split('\n')
    lines = [l.strip() for l in lines if l.strip()]

    data = {}
    rng = VALID_RANGES

    for i, line in enumerate(lines):
        next_line = lines[i + 1] if i + 1 < len(lines) else ''
        combined = line + ' ' + next_line

        # 매매기준가
        if ('매매' in line and '기준' in line) and '기준가' not in data:
            n = find_price(combined, *rng['기준가'])
            if n:
                data['기준가'] = f'{n} 원/g'

        # 살 때
        if ('살 때' in line or '살때' in line) and '살 때' not in data:
            n = find_price(combined, *rng['살때'])
            if n:
                data['살 때'] = f'{n} 원/g'

        # 팔 때
        if ('팔 때' in line or '팔때' in line) and '팔 때' not in data:
            n = find_price(combined, *rng['팔때'])
            if n:
                data['팔 때'] = f'{n} 원/g'

        # 전일대비
        if ('전일대비' in line or '전일 대비' in line) and '전일대비' not in data:
            direction = ''
            if '상승' in combined or '▲' in combined:
                direction = '▲ '
            elif '하락' in combined or '▼' in combined:
                direction = '▼ '
            n = find_price(combined, *rng['전일대비'])
            if n:
                pct = re.search(r'([+-]?\d+\.\d+)\s*%', combined)
                pct_str = f' ({pct.group(1)}%)' if pct else ''
                data['전일대비'] = f'{direction}{n} 원{pct_str}'

        # 국제금 / 달러시세
        if ('국제금' in line or '달러' in line or '$/온스' in line
                or '달러/온스' in line) and '국제금' not in data:
            n = find_price(combined, *rng['국제금'])
            if n:
                data['국제금'] = f'{n} 달러/온스'

        # 1돈 가격
        if ('1돈' in line or '한돈' in line) and '1돈' not in data:
            n = find_price(combined, *rng['1돈'])
            if n:
                data['1돈'] = f'{n} 원/돈'

    # 변동률 보완 (전일대비 못 찾은 경우)
    if '전일대비' not in data:
        pct = re.search(r'([+-]?\d+\.\d+)\s*%', body_text)
        if pct:
            sign = '▲' if not pct.group(1).startswith('-') else '▼'
            data['전일대비'] = f'{sign} {pct.group(1)}%'

    return data


def format_section(name, data):
    """한 소스의 데이터를 포맷"""
    if not data:
        return f'[ {name} ] 추출 실패'

    order = [
        ('기준가',   '기준가    '),
        ('전일대비', '전일대비  '),
        ('살 때',    '살 때    '),
        ('팔 때',    '팔 때    '),
        ('1돈',      '1돈(3.75g)'),
        ('국제금',   '국제금    '),
    ]

    lines = [f'[ {name} ]']
    for key, label in order:
        if key in data:
            lines.append(f'  {label} {data[key]}')

    return '\n'.join(lines)


def build_github_info():
    if not GITHUB_REPO:
        return ""
    run_url = f"{GITHUB_SERVER}/{GITHUB_REPO}/actions/runs/{GITHUB_RUN_ID}"
    return f"\n─────────────────────\n{run_url}"


def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    github_info = build_github_info()
    driver = create_driver()
    wait = WebDriverWait(driver, 15)

    image_files = []
    sections = []

    try:
        # 1) 스크린샷 캡처 (검색결과 페이지)
        for site in SCREENSHOT_SITES:
            print(f"\n{'='*40}")
            print(f"[캡처] {site['name']} 접속: {site['url']}")
            driver.get(site['url'])
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5)
            driver.save_screenshot(site['file'])
            image_files.append(site['file'])
            print(f"[캡처] {site['name']} 완료: {site['file']}")

        # 2) 텍스트 추출 (금융 페이지 - 네이버, 다음 각각)
        for source in TEXT_SOURCES:
            data = extract_gold_data(driver, source)
            section = format_section(source['name'], data)
            sections.append(section)
            print(f"\n{section}")

    except Exception as e:
        print(f"오류: {e}")
        driver.save_screenshot("error.png")
        send_discord_combined(f"금시세 캡처 오류\n```{e}```{github_info}", ["error.png"])
        return
    finally:
        driver.quit()

    # 3) Discord 전송 (텍스트 + 이미지 하나의 메시지)
    body = '\n\n'.join(sections)
    msg = f"**금시세 ({now})**\n```\n{body}\n```{github_info}"
    send_discord_combined(msg, image_files)

    print("\n모든 전송 완료")


if __name__ == "__main__":
    main()
