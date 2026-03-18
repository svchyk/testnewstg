import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re
import feedparser
import yfinance as yf
import google.generativeai as genai

# ==========================================
# 1. КОНФИГУРАЦИЯ
# ==========================================
DISPLAY_CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario', 'victorstepanych', 'varlamov_news']
ANALYSIS_CHANNELS = ['tasnim_khabar', 'farsna', 'Military_Arabic', 'intelsky', 'war_monitor']
RSS_FEEDS = [
    'https://www.aljazeera.com/xml/rss/all.xml',
    'https://www.timesofisrael.com/feed/',
    'https://news.google.com/rss/search?q=Associated+Press+Middle+East&hl=en-US'
]

ARCHIVE_FILE = 'archive.json'
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash') # Используем flash для стабильности
else:
    model = None

# ==========================================
# 2. СБОР ДАННЫХ
# ==========================================
def get_oil_price():
    try:
        oil = yf.Ticker("BZ=F") 
        return f"{oil.history(period='1d')['Close'].iloc[-1]:.2f}"
    except: return "92.50"

def get_reddit_rumors():
    rumors = []
    try:
        res = requests.get("https://www.reddit.com/r/MiddleEastNews/new.json?limit=15", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        for post in res.json()['data']['children']:
            rumors.append(post['data']['title'])
    except: pass
    return " | ".join(rumors)

def get_tg_posts(channel_name, limit=30):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.find('div', class_='tgme_channel_info_header_title')
        full_name = title.text.strip() if title else channel_name
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=limit)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            if not text_area: continue
            link = item.find('a', class_='tgme_widget_message_date').get('href')
            date_raw = item.find('time', class_='time').get('datetime')
            video = item.find('video')
            video_url = video.get('src') if video else ""
            img = ""
            photo = item.find('a', class_='tgme_widget_message_photo_wrap')
            if photo and "url('" in photo.get('style', ''):
                img = photo.get('style').split("url('")[1].split("')")[0]
            posts.append({
                'id': f"{channel_name}_{link.split('/')[-1]}",
                'full_name': full_name,
                'content': text_area.decode_contents(),
                'text_plain': text_area.get_text(separator=' '),
                'date_raw': date_raw,
                'link': link,
                'media': img,
                'video': video_url
            })
    except: pass
    return posts

# ==========================================
# 3. ОСНОВНОЙ ПРОЦЕСС
# ==========================================
def aggregate():
    feed_posts = []
    for ch in DISPLAY_CHANNELS:
        feed_posts.extend(get_tg_posts(ch, limit=40))
    
    feed_posts_sorted = sorted(feed_posts, key=lambda x: x['date_raw'], reverse=True)
    
    # Собираем контекст (50 постов)
    ai_context = "MAIN FEED:\n" + " ".join([p['text_plain'] for p in feed_posts_sorted[:50]])
    for ch in ANALYSIS_CHANNELS:
        extra = get_tg_posts(ch, limit=10)
        ai_context += "\nEXTRA:\n" + " ".join([e['text_plain'] for e in extra])

    ai_data = {
        "escalation": "80%", "nuclear_risk": "5%", "ground_op": "30%", "forecast_date": "21.03",
        "analysis": "Данные обрабатываются ИИ...", "rumors_block": "Мониторинг X/Reddit..."
    }

    if model:
        prompt = f"Analyze these news and return ONLY JSON: {{'escalation': 'X%', 'nuclear_risk': 'X%', 'ground_op': 'X%', 'forecast_date': 'DD.MM', 'analysis': '12 sentences of deep analysis', 'rumors_block': '12 sentences of rumors analysis'}}. Context: {ai_context[:5000]}"
        try:
            response = model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match: ai_data = json.loads(match.group().replace("'", '"'))
        except: pass

    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            try: archive = json.load(f)
            except: archive = []
    else: archive = []

    existing_ids = {p['id'] for p in archive}
    for np in feed_posts:
        if np['id'] not in existing_ids: archive.append(np)
    
    archive.sort(key=lambda x: x['date_raw'], reverse=True)
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive[:1000], f, ensure_ascii=False, indent=2)

    now_msk = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).strftime("%H:%M")

    # Генерируем HTML по частям, чтобы избежать ошибок с длинными строками
    html_start = f'''<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>Intelligence Center</title>
    <style>
        :root {{ --bg: #f2f2f7; --card: #ffffff; --text: #000; --accent: #007aff; --rumor: #ff9500; }}
        [data-theme="dark"] {{ --bg: #000; --card: #1c1c1e; --text: #fff; --accent: #0a84ff; --rumor: #ff9f0a; }}
        body {{ background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; margin: 0; padding-bottom: 100px; }}
        header {{ position: sticky; top: 0; z-index: 1000; background: rgba(255,255,255,0.8); backdrop-filter: blur(20px); padding: 15px 20px; border-bottom: 0.5px solid rgba(0,0,0,0.1); display:flex; justify-content:space-between; }}
        .summary-card {{ background: var(--card); border-radius: 25px; padding: 25px; margin: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .stat-box {{ background: rgba(120,120,128,0.08); padding: 12px; border-radius: 15px; }}
        .stat-val {{ font-size: 20px; font-weight: 900; color: var(--accent); display: block; }}
        .card {{ background: var(--card); border-radius: 20px; padding: 20px; margin: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }}
        .media-img, video {{ width: 100%; border-radius: 15px; margin-bottom: 15px; }}
        .rumors-section {{ margin-top:15px; padding:15px; background:rgba(255,149,0,0.1); border-left:4px solid var(--rumor); border-radius:10px; font-size:14px; }}
        .tabs {{ position: fixed; bottom: 0; width: 100%; background: var(--card); display: flex; padding: 15px 0 30px 0; border-top: 0.5px solid rgba(0,0,0,0.1); }}
        .tab {{ flex: 1; text-align: center; text-decoration: none; color: #8e8e93; font-size: 10px; }}
        .tab.active {{ color: var(--accent); }}
    </style>
</head>
<body data-theme="dark">
<header>
    <b style="font-size:20px;">Intelligence</b>
    <span>{now_msk} MSK</span>
</header>
<div style="max-width:600px; margin: 0 auto;">
    <div class="summary-card">
        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">{ai_data['escalation']}</span></div>
            <div class="stat-box">Ядерный риск<span class="stat-val">{ai_data['nuclear_risk']}</span></div>
            <div class="stat-box">Наземная оп.<span class="stat-val">{ai_data['ground_op']}</span></div>
            <div class="stat-box">Прогноз<span class="stat-val">{ai_data['forecast_date']}</span></div>
        </div>
        <p style="font-size:14px; line-height:1.6; margin-top:20px;">{ai_data['analysis']}</p>
        <div class="rumors-section"><b>СЛУХИ:</b> {ai_data['rumors_block']}</div>
    </div>
    <div id="feed"></div>
</div>
<div class="tabs">
    <a href="#" class="tab active">📰 СВОДКА</a>
    <a href="#" class="tab">📦 АРХИВ</a>
</div>
<script>
    const posts = {json.dumps(archive[:100])};
    document.getElementById('feed').innerHTML = posts.map(p => `
        <div class="card">
            ${{p.video ? `<video src="${{p.video}}" controls></video>` : (p.media ? `<img src="${{p.media}}" class="media-img">` : '')}}
            <div style="font-weight:800; color:var(--accent);">${{p.full_name}}</div>
            <div style="font-size:15px; margin-top:10px;">${{p.content}}</div>
        </div>
    `).join('');
</script>
</body></html>'''

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_start)

if __name__ == "__main__":
    aggregate()
