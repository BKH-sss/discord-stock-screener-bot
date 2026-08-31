import os
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

KR_DISCORD_WEBHOOK_URL = os.getenv("KR_DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL", "")
US_DISCORD_WEBHOOK_URL = os.getenv("US_DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL", "")

def fetch_kr_stock_news(limit=7):
    """
    네이버 금융 국내 주요 주식 뉴스 실시간 크롤링
    """
    url = "https://finance.naver.com/news/mainnews.naver"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    news_items = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content.decode('cp949', errors='ignore'), 'html.parser')
        
        articles = soup.select('ul.newsList li.block1')
        for li in articles:
            title_tag = li.select_one('dd.articleSubject a')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = title_tag.get('href', '')
            if link.startswith('/'):
                link = "https://finance.naver.com" + link
                
            summary_tag = li.select_one('dd.articleSummary')
            summary = ""
            press = ""
            if summary_tag:
                press_tag = summary_tag.select_one('span.press')
                if press_tag:
                    press = press_tag.get_text(strip=True)
                # 요약문 추출
                summary = summary_tag.get_text(strip=True)
                if press:
                    summary = summary.replace(press, '').strip()
                summary = summary.split('\n')[0][:80] + "..." if len(summary) > 80 else summary
                
            news_items.append({
                'title': title,
                'link': link,
                'press': press,
                'summary': summary
            })
            if len(news_items) >= limit:
                break
    except Exception as e:
        print(f"[!] 국내 뉴스 크롤링 중 오류: {e}")
        
    return news_items

def fetch_us_stock_news(limit=7):
    """
    Yahoo Finance 기반 미국 시장 주요 뉴스 수집
    """
    news_items = []
    try:
        # 대표 지수 ETF (SPY) 및 빅테크 종목 뉴스 취합
        spy = yf.Ticker('SPY')
        raw_news = spy.news or []
        
        for item in raw_news:
            content = item.get('content', {})
            title = content.get('title')
            summary = content.get('summary', '')
            provider = content.get('provider', {}).get('displayName', 'Yahoo Finance')
            click_url = content.get('clickThroughUrl', {}).get('url') or content.get('canonicalUrl', {}).get('url')
            
            if not title or not click_url:
                continue
                
            if len(summary) > 100:
                summary = summary[:100] + "..."
                
            news_items.append({
                'title': title,
                'link': click_url,
                'press': provider,
                'summary': summary
            })
            if len(news_items) >= limit:
                break
    except Exception as e:
        print(f"[!] 미국 뉴스 수집 중 오류: {e}")
        
    return news_items

def send_kr_news_to_discord(news_list):
    if not KR_DISCORD_WEBHOOK_URL or "http" not in KR_DISCORD_WEBHOOK_URL:
        print("[!] KR_DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")
        return
        
    today_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    fields = []
    for i, item in enumerate(news_list, 1):
        press_str = f" [{item['press']}]" if item['press'] else ""
        fields.append({
            "name": f"{i}. {item['title']}{press_str}",
            "value": f"{item['summary']}\n👉 [기사 전문 읽기]({item['link']})",
            "inline": False
        })
        
    embed = {
        "title": "📰 [국내 증시] 모닝 주요 헤드라인 뉴스",
        "description": "오늘 아침 국내 주식 시장 핵심 뉴스 브리핑입니다.",
        "color": 3447003, # Blue
        "fields": fields,
        "footer": {"text": f"발송 시각: {today_str} | 출처: 네이버 금융"}
    }
    
    payload = {
        "username": "🇰🇷 국내증시 뉴스봇",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Flag_of_South_Korea.svg/800px-Flag_of_South_Korea.svg.png",
        "embeds": [embed]
    }
    
    resp = requests.post(KR_DISCORD_WEBHOOK_URL, json=payload)
    if resp.status_code in [200, 204]:
        print("[+] 국내 주식 뉴스 디스코드 전송 완료!")
    else:
        print(f"[!] 국내 뉴스 전송 실패: {resp.status_code}, {resp.text}")

def send_us_news_to_discord(news_list):
    if not US_DISCORD_WEBHOOK_URL or "http" not in US_DISCORD_WEBHOOK_URL:
        print("[!] US_DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")
        return
        
    today_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    fields = []
    for i, item in enumerate(news_list, 1):
        press_str = f" [{item['press']}]" if item['press'] else ""
        fields.append({
            "name": f"{i}. {item['title']}{press_str}",
            "value": f"{item['summary']}\n👉 [Read Article]({item['link']})",
            "inline": False
        })
        
    embed = {
        "title": "🗽 [미국 증시] 모닝 글로벌 마켓 헤드라인 뉴스",
        "description": "오늘 아침 미국 주식 시장 및 글로벌 거시경제 핵심 뉴스 브리핑입니다.",
        "color": 15105570, # Orange
        "fields": fields,
        "footer": {"text": f"발송 시각: {today_str} | Source: Yahoo Finance"}
    }
    
    payload = {
        "username": "🇺🇸 미국증시 뉴스봇",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Flag_of_the_United_States.svg/800px-Flag_of_the_United_States.svg.png",
        "embeds": [embed]
    }
    
    resp = requests.post(US_DISCORD_WEBHOOK_URL, json=payload)
    if resp.status_code in [200, 204]:
        print("[+] 미국 주식 뉴스 디스코드 전송 완료!")
    else:
        print(f"[!] 미국 뉴스 전송 실패: {resp.status_code}, {resp.text}")

def main():
    print(f"[{datetime.now()}] 국내/해외 주식 최신 뉴스 수집 및 발송 시작...")
    kr_news = fetch_kr_stock_news(limit=7)
    if kr_news:
        send_kr_news_to_discord(kr_news)
        
    us_news = fetch_us_stock_news(limit=7)
    if us_news:
        send_us_news_to_discord(us_news)

if __name__ == "__main__":
    main()
