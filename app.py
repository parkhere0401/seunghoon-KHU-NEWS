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

# --- [매체 티어 및 도메인 매핑 데이터] ---
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
    "hankookilbo.com": ("한국일보", 2), "newsis.com": ("뉴시스", 2), "news1.kr": ("뉴스1", 2),
    "edaily.co.kr": ("이데일리", 2), "mt.co.kr": ("머니투데이", 2), "sedaily.com": ("서울경제", 2),
    "akomnews.com": ("한의신문", 3), "mjmedi.com": ("민족의학신문", 3)
}

NATE_CPCD_MAPPER = {
    "sed": ("서울경제", 2), "chosun": ("조선일보", 1), "joongang": ("중앙일보", 1),
    "donga": ("동아일보", 1), "mk": ("매일경제", 1), "hk": ("한국경제", 1),
    "hkr": ("한겨레", 1), "kh": ("경향신문", 1), "cn": ("국민일보", 1),
    "yna": ("연합뉴스", 1), "ytn": ("YTN", 1), "news1": ("뉴스1", 2), "newsis": ("뉴시스", 2)
}

BLACKLIST_DOMAINS = [
    "blog.naver.com", "tistory.com", "brunch.co.kr", "egloos.com", 
    "contents.premium.naver.com", "namu.wiki", "youtube.com", "facebook.com", "instagram.com"
]

# --- [도움 함수] ---
def get_tier_info(url, source_name):
    try:
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.replace("www.", "").replace("m.", "")
        if "nate.com" in domain:
            params = urllib.parse.parse_qs(parsed_url.query)
            cpcd = params.get('cpcd', [''])[0]
            if cpcd in NATE_CPCD_MAPPER: return NATE_CPCD_MAPPER[cpcd][0], NATE_CPCD_MAPPER[cpcd][1]
        for tier, names in TIER_DATA.items():
            for name in names:
                if name in source_name: return name, tier
        parts = domain.split('.')
        for i in range(len(parts)):
            sub = ".".join(parts[i:])
            if sub in TIER_MAPPER: return TIER_MAPPER[sub][0], TIER_MAPPER[sub][1]
        return domain, 4
    except: return source_name, 4

def parse_to_datetime(date_str):
    formats = ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S GMT', '%Y-%m-%d %H:%M:%S']
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=None)
        except: continue
