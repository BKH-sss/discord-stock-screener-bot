import os
import time
import requests
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("KR_DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL", "")

def get_krx_universe(limit=250):
    """
    FinanceDataReader로 시가총액 상위 코스피/코스닥 종목 리스트 가져오기
    """
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx = df_krx.dropna(subset=['Marcap']).sort_values(by='Marcap', ascending=False)
        
        items = []
        for _, row in df_krx.head(limit).iterrows():
            code = str(row['Code'])
            market = str(row['Market'])
            name = str(row['Name'])
            
            # yfinance 티커 형태 (.KS: 코스피, .KQ: 코스닥)
            suffix = ".KS" if "KOSPI" in market else ".KQ"
            yf_ticker = f"{code}{suffix}"
            
            items.append({
                'code': code,
                'yf_ticker': yf_ticker,
                'name': name,
                'market': market
            })
        return items
    except Exception as e:
        print(f"[!] KRX 목록 수집 중 오류: {e}")
        return []

def analyze_kr_stock(item):
    """
    단일 국내 종목 재무 데이터 분석 (yfinance 기반 정밀 수집)
    - 부채비율 120% 이하 (Debt / Equity <= 1.2)
    - 최근 3개년 자산 증가율, 영업이익 증가율, 매출액 증가율
    """
    yf_ticker = item['yf_ticker']
    code = item['code']
    name = item['name']
    
    try:
        stock = yf.Ticker(yf_ticker)
        bs = stock.balance_sheet
        fin = stock.financials
        
        if bs.empty or fin.empty:
            return None
        
        # 연간 데이터 컬럼 오름차순 정렬 (과거 -> 최근)
        bs = bs.sort_index(axis=1)
        fin = fin.sort_index(axis=1)
        
        if len(bs.columns) < 4 or len(fin.columns) < 4:
            return None
            
        col_old = bs.columns[-4]   # 3년 전
        col_curr = bs.columns[-1]  # 최근 연도
        
        # 1. 부채비율 확인
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
        
        # 부채비율 120% 초과시 제외
        if debt_to_equity > 120.0:
            return None
            
        # 2. 자산 증가율 (3개년)
        if 'Total Assets' not in bs.index:
            return None
        asset_old = bs.loc['Total Assets', col_old]
        asset_curr = bs.loc['Total Assets', col_curr]
        if pd.isna(asset_old) or pd.isna(asset_curr) or asset_old <= 0:
            return None
        asset_growth = ((asset_curr - asset_old) / asset_old) * 100.0
        
        # 3. 영업이익 증가율 (3개년)
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
        
        # 4. 매출액 증가율 (3개년)
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
        
        return {
            'code': code,
            'name': name,
            'debt_ratio': round(debt_to_equity, 2),
            'asset_growth': round(asset_growth, 2),
            'op_growth': round(op_growth, 2),
            'rev_growth': round(rev_growth, 2)
        }
    except Exception:
        return None

def fetch_and_screen_krx(limit=250):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 국내 주식(KOSPI/KOSDAQ) 재무 데이터 스크리닝 시작...")
    items = get_krx_universe(limit=limit)
    print(f"시가총액 상위 {len(items)}개 종목 분석 중...")
    
    results = []
    for i, item in enumerate(items):
        res = analyze_kr_stock(item)
        if res:
            results.append(res)
        if (i + 1) % 25 == 0 or (i + 1) == len(items):
            print(f"진행 상황: {i+1}/{len(items)} 완료 (부채비율 120% 이하 통과: {len(results)}개)")
        time.sleep(0.05)
        
    df = pd.DataFrame(results)
    if df.empty:
        print("[!] 필터링 조건을 만족하는 국내 종목이 없습니다.")
        return None
        
    print(f"최종 통과 종목 수: {len(df)}개")
    return df

def send_krx_to_discord(df):
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
            name_clean = str(row['name'])[:10]
            lines.append(f"{rank:2d}위 **{name_clean}** ({row['code']}) : **+{val:,.1f}{metric_unit}** *(부채: {debt:.1f}%)*")
        return "\n".join(lines)
    
    embeds = [
        {
            "title": f"🇰🇷 [국내장] 최근 3개년 자산 증가율 TOP 20",
            "description": f"**조건: 부채비율 120% 이하**\n\n" + format_list(top_asset, 'asset_growth'),
            "color": 3447003, # Blue
            "footer": {"text": f"기준일자: {today_str} | Data by Yahoo Finance"}
        },
        {
            "title": f"🚀 [국내장] 최근 3개년 영업이익 증가율 TOP 20",
            "description": f"**조건: 부채비율 120% 이하**\n\n" + format_list(top_op, 'op_growth'),
            "color": 15105570, # Orange
            "footer": {"text": f"기준일자: {today_str} | Data by Yahoo Finance"}
        },
        {
            "title": f"📈 [국내장] 최근 3개년 매출액 증가율 TOP 20",
            "description": f"**조건: 부채비율 120% 이하**\n\n" + format_list(top_rev, 'rev_growth'),
            "color": 5763719, # Green
            "footer": {"text": f"기준일자: {today_str} | Data by Yahoo Finance"}
        }
    ]
    
    payload = {
        "username": "🇰🇷 국내주식 스크리너 봇",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Flag_of_South_Korea.svg/800px-Flag_of_South_Korea.svg.png",
        "content": f"🔔 **[{today_str}] 국내 주식(KOSPI/KOSDAQ) 3개년 성장성 TOP 20 리포트 (부채비율 120% 이하)**",
        "embeds": embeds
    }
    
    resp = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if resp.status_code == 204:
        print("[+] 국내 주식 디스코드 리포트 전송 완료!")
    else:
        print(f"[!] 디스코드 전송 실패 (상태코드: {resp.status_code}): {resp.text}")

def main():
    df = fetch_and_screen_krx(limit=250)
    if df is not None:
        send_krx_to_discord(df)

if __name__ == "__main__":
    main()
