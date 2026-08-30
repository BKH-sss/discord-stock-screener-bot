import os
import time
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("US_DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL", "")

def get_sp500_tickers():
    """S&P 500 종목 리스트 가져오기"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        html = requests.get(url, headers=headers).text
        tables = pd.read_html(html)
        df = tables[0]
        tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
        return tickers
    except Exception as e:
        print(f"[!] S&P 500 티커 수집 실패, 기본 대표 티커 사용: {e}")
        return [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "AVGO",
            "JPM", "UNH", "V", "XOM", "MA", "COST", "HD", "PG", "NFLX", "JNJ",
            "BAC", "ABBV", "CRM", "KO", "MRK", "ORCL", "AMD", "WMT", "PEP", "CVX",
            "ADBE", "TMO", "ACN", "QCOM", "LIN", "MCD", "CSCO", "ABT", "INTU", "TXN",
            "AMAT", "DHR", "CAT", "GE", "IBM", "PFE", "NOW", "AMGN", "VZ", "MS"
        ]

def analyze_stock(ticker):
    """단일 미국 종목의 재무 데이터 분석"""
    try:
        stock = yf.Ticker(ticker)
        bs = stock.balance_sheet
        fin = stock.financials
        
        if bs.empty or fin.empty:
            return None
        
        bs = bs.sort_index(axis=1)
        fin = fin.sort_index(axis=1)
        
        if len(bs.columns) < 4 or len(fin.columns) < 4:
            return None
            
        col_old = bs.columns[-4]
        col_curr = bs.columns[-1]
        
        # 1. 부채비율
        debt = None
        equity = None
        if 'Total Debt' in bs.index:
            debt = bs.loc['Total Debt', col_curr]
        elif 'Total Liabilities Net Minority Interest' in bs.index:
            debt = bs.loc['Total Liabilities Net Minority Interest', col_curr]
            
        if 'Stockholders Equity' in bs.index:
            equity = bs.loc['Stockholders Equity', col_curr]
        elif 'Total Equity Gross Minority Interest' in bs.index:
            equity = bs.loc['Total Equity Gross Minority Interest', col_curr]
            
        if pd.isna(debt) or pd.isna(equity) or equity <= 0:
            return None
            
        debt_to_equity = (debt / equity) * 100.0
        if debt_to_equity > 120.0:
            return None
            
        # 2. 자산 증가율
        if 'Total Assets' not in bs.index:
            return None
        asset_old = bs.loc['Total Assets', col_old]
        asset_curr = bs.loc['Total Assets', col_curr]
        if pd.isna(asset_old) or pd.isna(asset_curr) or asset_old <= 0:
            return None
        asset_growth = ((asset_curr - asset_old) / asset_old) * 100.0
        
        # 3. 영업이익 증가율
        op_inc_field = None
        for field in ['Operating Income', 'Operating Revenue']:
            if field in fin.index:
                op_inc_field = field
                break
        if not op_inc_field:
            return None
            
        op_inc_old = fin.loc[op_inc_field, col_old]
        op_inc_curr = fin.loc[op_inc_field, col_curr]
        if pd.isna(op_inc_old) or pd.isna(op_inc_curr) or op_inc_old <= 0:
            return None
        op_growth = ((op_inc_curr - op_inc_old) / op_inc_old) * 100.0
        
        # 4. 매출액 증가율
        rev_field = None
        for field in ['Total Revenue', 'Operating Revenue']:
            if field in fin.index:
                rev_field = field
                break
        if not rev_field:
            return None
            
        rev_old = fin.loc[rev_field, col_old]
        rev_curr = fin.loc[rev_field, col_curr]
        if pd.isna(rev_old) or pd.isna(rev_curr) or rev_old <= 0:
            return None
        rev_growth = ((rev_curr - rev_old) / rev_old) * 100.0
        
        name = ticker
        try:
            info = stock.info
            name = info.get('shortName', ticker)
        except Exception:
            pass
            
        return {
            'ticker': ticker,
            'name': name,
            'debt_ratio': round(debt_to_equity, 2),
            'asset_growth': round(asset_growth, 2),
            'op_growth': round(op_growth, 2),
            'rev_growth': round(rev_growth, 2)
        }
    except Exception:
        return None

def fetch_and_screen(limit=None):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 미국 주식 재무 데이터 스크리닝 시작...")
    tickers = get_sp500_tickers()
    if limit:
        tickers = tickers[:limit]
    print(f"총 {len(tickers)}개 종목 분석 중...")
    
    results = []
    for i, t in enumerate(tickers):
        res = analyze_stock(t)
        if res:
            results.append(res)
        if (i + 1) % 20 == 0 or (i + 1) == len(tickers):
            print(f"진행 상황: {i+1}/{len(tickers)} 완료 (조건 통과: {len(results)}개)")
        time.sleep(0.05)
        
    df = pd.DataFrame(results)
    if df.empty:
        print("[!] 필터링 조건을 만족하는 종목이 없습니다.")
        return None
        
    print(f"부채비율 120% 이하 통과 종목 수: {len(df)}개")
    return df

def send_to_discord(df):
    if not DISCORD_WEBHOOK_URL or "http" not in DISCORD_WEBHOOK_URL:
        print("[!] DISCORD_WEBHOOK_URL이 올바르지 않습니다.")
        return
        
    top_asset = df.sort_values(by='asset_growth', ascending=False).head(20)
    top_op = df.sort_values(by='op_growth', ascending=False).head(20)
    top_rev = df.sort_values(by='rev_growth', ascending=False).head(20)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    def format_list(subset, metric_key, metric_unit='%'):
        lines = []
        for rank, (_, row) in enumerate(subset.iterrows(), 1):
            val = row[metric_key]
            debt = row['debt_ratio']
            name_clean = str(row['name'])[:15]
            lines.append(f"{rank:2d}위 **{row['ticker']}** ({name_clean}) : **+{val:.1f}{metric_unit}** *(부채: {debt:.1f}%)*")
        return "\n".join(lines)
    
    embeds = [
        {
            "title": f"📊 [미국장] 3개년 자산 증가율 TOP 20",
            "description": f"**조건: 부채비율 120% 이하**\n\n" + format_list(top_asset, 'asset_growth'),
            "color": 3447003,
            "footer": {"text": f"기준일자: {today_str} | Data by Yahoo Finance"}
        },
        {
            "title": f"🚀 [미국장] 3개년 영업이익 증가율 TOP 20",
            "description": f"**조건: 부채비율 120% 이하**\n\n" + format_list(top_op, 'op_growth'),
            "color": 15105570,
            "footer": {"text": f"기준일자: {today_str} | Data by Yahoo Finance"}
        },
        {
            "title": f"📈 [미국장] 3개년 매출액 증가율 TOP 20",
            "description": f"**조건: 부채비율 120% 이하**\n\n" + format_list(top_rev, 'rev_growth'),
            "color": 5763719,
            "footer": {"text": f"기준일자: {today_str} | Data by Yahoo Finance"}
        }
    ]
    
    payload = {
        "username": "🇺🇸 미국주식 스크리너 봇",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Flag_of_the_United_States.svg/800px-Flag_of_the_United_States.svg.png",
        "content": f"🔔 **[{today_str}] 미국 주식 3개년 성장성 TOP 20 리포트 (부채비율 120% 이하)**",
        "embeds": embeds
    }
    
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if resp.status_code == 204:
        print("[+] 미국 주식 디스코드 리포트 전송 완료!")
    else:
        print(f"[!] 디스코드 전송 실패 (상태코드: {resp.status_code}): {resp.text}")

def main():
    df = fetch_and_screen()
    if df is not None:
        send_to_discord(df)

if __name__ == "__main__":
    main()
