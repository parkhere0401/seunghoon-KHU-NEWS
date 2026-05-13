import streamlit as st
import feedparser
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta
import urllib.parse
import re

# 1. 페이지 설정
st.set_page_config(page_title="경희대학교 및 의료기관 뉴스 클리핑", page_icon="🏫", layout="wide")

# API 키
NAVER_CLIENT_ID = "_FNNM0QDYA8u84RC8qFE" 
NAVER_CLIENT_SECRET = "oPX8YNZK6m"

if 'news_list' not in st.session_state:
    st.session_state.news_list = []

# --- [데이터 정의: 티어 및 매퍼] ---
TIER_DATA = {
    1: ["조선일보", "중앙일보", "동아일보", "매일경제", "한국경제", "한겨레", "경향신문", "국민일보", "연합뉴스", "YTN", "SBS", "KBS", "MBC", "JTBC"],
    2: ["한국일보", "문화일보", "서울신문", "세계일보", "머니투데이", "서울경제", "뉴시스", "뉴스1", "파이낸셜뉴스", "조선비즈", "이데일리", "한국경제TV", "아시아경제", "연합뉴스TV", "MBN", "채널A", "EBS"],
    3: ["헤럴드경제", "전자신문", "오마이뉴스", "머니S", "매일신문", "아이뉴스24", "프레시안", "부산일보", "더팩트", "노컷뉴스", "블로터", "미디어오늘", "디지털데일리", "조세일보", "디지털타임스", "SBS Biz", "데일리안", "TV조선", "강원일보", "코리아헤럴드", "쿠키뉴스", "KTV", "IT동아", "한의신문", "민족의학신문", "매일일보", "로리더", "신아일보", "시사IN", "시사저널"]
}

TIER_MAPPER = {
    "chosun.com": ("조선일보", 1), "joongang.co.kr": ("중앙일보", 1), "donga.com": ("동아일보", 1),
    "mk.co.kr": ("매일경제", 1), "hankyung.com": ("한국경제", 1), "hani.co.kr": ("한겨레", 1),
    "khan.co.kr": ("경향신문", 1), "kmib.co.kr": ("국민일보", 1), "yna.co.kr": ("연합뉴스", 1),
    "ytn.co.kr": ("YTN", 1), "sbs.co.kr": ("SBS", 1), "kbs.co.kr": ("KBS", 1),
    "imbc.com": ("MBC", 1), "jtbc.co.kr": ("JTBC", 1),
}

BLACKLIST_DOMAINS = ["blog.naver.com", "tistory.com", "brunch.co.kr", "namu.wiki", "contents.premium.naver.com", "youtube.com", "facebook.com", "instagram.com"]

# --- [유틸리티 함수] ---
def get_tier_info(url, source_name):
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace("www.", "").replace("m.", "")
        if "nate.com" in domain:
            cpcd = urllib.parse.parse_qs(parsed.query).get('cpcd', [''])[0]
            codes = {"sed": ("서울경제", 2), "chosun": ("조선일보", 1), "joongang": ("중앙일보", 1)}
            if cpcd in codes: return codes[cpcd]
        for tier, names in TIER_DATA.items():
            for name in names:
                if name in source_name: return name, tier
        parts = domain.split('.')
        for i in range(len(parts)):
            sub = ".".join(parts[i:])
            if sub in TIER_MAPPER: return TIER_MAPPER[sub]
        return domain, 4
    except: return source_name, 4

def parse_date(date_str):
    for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%d %H:%M:%S']:
        try: return datetime.strptime(date_str, fmt).replace(tzinfo=None)
        except: continue
    return datetime.now()

def extract_professor(title):
    match = re.search(r'([가-힣]{2,4}\s?교수)', title)
    return match.group(1) if match else "-"

# --- [뉴스 수집 로직] ---
def fetch_news(days):
    keywords = "경희대 | 경희대학교 | 경희의료원 | 강동경희대학교병원 | 강동경희"
    n_url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(keywords)}&display=100&sort=date"
    n_res = requests.get(n_url, headers={"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}, timeout=10).json()
    start = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    g_q = f"(\"경희대\" OR \"경희대학교\") after:{start} " + " ".join([f"-site:{b}" for b in BLACKLIST_DOMAINS])
    g_f = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(g_q)}&hl=ko&gl=KR&ceid=KR:ko")

    temp = []
    for item in n_res.get('items', []):
        if any(b in item['link'] for b in BLACKLIST_DOMAINS): continue
        name, tier = get_tier_info(item['originallink'], "Naver News")
        temp.append({"title": item['title'].replace("<b>","").replace("</b>",""), "link": item['link'], "source": name, "date": item['pubDate'], "type": "Naver", "tier": tier})
    for entry in g_f.entries:
        if "Google News" in entry.source.title: continue
        name, tier = get_tier_info(entry.link, entry.source.title)
        temp.append({"title": entry.title, "link": entry.link, "source": name, "date": entry.published, "type": "Google", "tier": tier})

    seen, final = set(), []
