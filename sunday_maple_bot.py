"""
메이플스토리 썬데이 메이플 디스코드 웹훅 알리미
- 메이플스토리 이벤트 페이지를 크롤링하여 최신 썬데이 메이플 공지와 이미지를 디스코드 채널로 전송합니다.
"""

import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import json
import os

# ==========================================
# 설정 (Configuration)
# ==========================================
# 디스코드 채널 설정 -> 연동 -> 웹훅 만들기 -> 웹훅 URL 복사 후 아래에 붙여넣으세요.
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1543098119242121356/GBqBrwqAVQnbrEFpJDm_D7LmnvleIHIMq9ogPgAEkzOmOSm8uzhFO-QV2Mn1s7zozbHS"

# 메이플스토리 이벤트 목록 URL
MAPLE_EVENT_URL = "https://maplestory.nexon.com/News/Event"
BASE_URL = "https://maplestory.nexon.com"

# 마지막으로 전송한 이벤트 링크를 저장할 파일 (중복 전송 방지용)
LAST_SENT_FILE = "last_sunday_maple.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_latest_sunday_maple():
    """메이플 공식 홈페이지에서 최신 썬데이 메이플 이벤트 정보를 크롤링합니다."""
    try:
        res = requests.get(MAPLE_EVENT_URL, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        items = soup.select(".event_list_wrap")
        for item in items:
            dd_a = item.select_one("dd.data p a")
            if not dd_a:
                continue

            title = dd_a.get_text(strip=True)

            # '썬데이' 키워드가 들어간 최신 이벤트 탐색
            if "썬데이" in title:
                dt_a = item.select_one("dt a")
                link = urljoin(BASE_URL, dt_a["href"]) if dt_a and dt_a.has_attr("href") else ""
                
                # 썸네일 이미지
                thumb_img = item.select_one("dt img")
                thumb_url = thumb_img["src"] if thumb_img and thumb_img.has_attr("src") else ""

                # 이벤트 기간
                date_tag = item.select_one("dd.date")
                date_str = date_tag.get_text(strip=True) if date_tag else ""

                # 상세 페이지 본문 이미지 파싱 (썬데이 혜택 안내 큰 이미지)
                main_image_url = get_detail_image(link) or thumb_url

                return {
                    "title": title,
                    "link": link,
                    "date": date_str,
                    "thumbnail": thumb_url,
                    "image": main_image_url
                }

    except Exception as e:
        print(f"[{datetime.now()}] 크롤링 중 오류 발생: {e}")
    return None


def get_detail_image(detail_url):
    """상세 페이지 내의 본문 안내 이미지 URL을 추출합니다."""
    if not detail_url:
        return None
    try:
        res = requests.get(detail_url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(detail_url_html := res.text, "html.parser")

        # 본문 영역 이미지 탐색 (.qs_text, .board_view_con 등)
        content = soup.select_one(".qs_text, .event_view_con, .board_view_con, .view_cont")
        if content:
            imgs = content.find_all("img")
            if imgs:
                return imgs[0].get("src")
    except Exception as e:
        print(f"[{datetime.now()}] 상세 페이지 이미지 파싱 오류: {e}")
    return None


def send_discord_webhook(event_data):
    """디스코드 웹훅으로 Embed 메시지를 전송합니다."""
    if not DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URL == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        print("[!] DISCORD_WEBHOOK_URL을 먼저 입력해주세요.")
        return False

    embed = {
        "title": f"🍁 {event_data['title']}",
        "url": event_data["link"],
        "description": f"**이벤트 기간:** {event_data['date']}\n\n이번 주 썬데이 메이플 혜택을 확인해보세요!",
        "color": 16753920,  # 메이플 주황색 (Hex: #FFA500)
        "image": {
            "url": event_data["image"]
        },
        "thumbnail": {
            "url": event_data["thumbnail"]
        },
        "footer": {
            "text": "메이플스토리 공식 홈페이지 소식"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    payload = {
        "username": "썬데이 메이플 알리미",
        "avatar_url": "https://lwi.nexon.com/maplestory/common/meta.png",
        "embeds": [embed]
    }

    try:
        res = requests.post(
            DISCORD_WEBHOOK_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10
        )
        if res.status_code in [200, 204]:
            print(f"[{datetime.now()}] 디스코드 전송 완료: {event_data['title']}")
            return True
        else:
            print(f"[{datetime.now()}] 디스코드 전송 실패 (상태 코드: {res.status_code}): {res.text}")
    except Exception as e:
        print(f"[{datetime.now()}] 디스코드 요청 중 에러: {e}")
    return False


def check_and_notify():
    """새로운 썬데이 메이플이 올라왔는지 확인하고 전송합니다."""
    event = get_latest_sunday_maple()
    if not event:
        print(f"[{datetime.now()}] 현재 썬데이 메이플 이벤트를 찾을 수 없습니다.")
        return

    # 마지막으로 전송한 링크 읽기
    last_sent_link = ""
    if os.path.exists(LAST_SENT_FILE):
        with open(LAST_SENT_FILE, "r", encoding="utf-8") as f:
            last_sent_link = f.read().strip()

    # 이미 전송된 이벤트인 경우 건너뜀
    if event["link"] == last_sent_link:
        print(f"[{datetime.now()}] 이미 전송된 최신 썬데이 메이플입니다. ({event['title']})")
        return

    # 웹훅 전송
    success = send_discord_webhook(event)
    if success:
        # 전송 성공 시 기록
        with open(LAST_SENT_FILE, "w", encoding="utf-8") as f:
            f.write(event["link"])


if __name__ == "__main__":
    print("=== 메이플스토리 썬데이 메이플 알리미 실행 ===")
    check_and_notify()
