import time
import schedule
from datetime import datetime
from stock_bot import main as run_us_bot
from korea_stock_bot import main as run_krx_bot

def job():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 아침 7시 48분 정기 알림 작업을 시작합니다.")
    
    # 1. 국내 주식(코스피/코스닥) 스크리닝 & 전송
    try:
        print(">> [1/2] 국내 주식 스크리닝 실행 중...")
        run_krx_bot()
    except Exception as e:
        print(f"[!] 국내 주식 리포트 실행 중 오류: {e}")
        
    time.sleep(5)
    
    # 2. 미국 주식(S&P 500) 스크리닝 & 전송
    try:
        print(">> [2/2] 미국 주식 스크리닝 실행 중...")
        run_us_bot()
    except Exception as e:
        print(f"[!] 미국 주식 리포트 실행 중 오류: {e}")

# 매일 아침 07:48에 실행 등록
schedule.every().day.at("07:48").do(job)

if __name__ == "__main__":
    print("=== [한/미 주식 3개년 성장성 TOP 20 디스코드 봇] ===")
    print("매일 아침 07:48에 국내/미국 주식 리포트가 전송되도록 대기 중입니다. (종료: Ctrl + C)")
    
    while True:
        schedule.run_pending()
        time.sleep(30)
