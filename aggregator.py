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

ARCHIVE_FILE = 'archive.json'
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# ==========================================
# 2. ФУНКЦИИ СБОРА
# ==========================================

def get_oil_price():
    try:
        oil = yf.Ticker("BZ=F") 
        price = oil.history(period='1d')['Close'].iloc[-1]
        return f"{price:.2f}"
    except: return "92.50"

def get_reddit_rumors():
    rumors = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get("https://www.reddit.com/r/MiddleEastNews/new.json?limit=15", headers=headers, timeout=10)
        data = res.json()
        for post in data['data']['children']:
            rumors.append(post['data']['title'])
    except: pass
    return " | ".join(rumors)

def get_tg_posts(channel_name, limit=50):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.encoding = 'utf-8'
        if response.status_code != 200: return []
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('div', class_='tgme_channel_info_header_title')
        full_name = title_tag.text.strip() if title_tag else channel_name
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=limit)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            if not text_area: continue
            content_html = text_area.decode_contents().strip()
            link_area = item.find('a', class_='tgme_widget_message_date')
            date_area = item.find('time', class_='time')
            if not link_area: continue
            video_url = ""
            video_tag = item.find('video')
            if video_tag: video_url = video_tag.get('src', '')
            media_url = ""
            photo = item.find('a', class_='tgme_widget_message_photo_wrap')
            video_thumb = item.find('i', class_='tgme_widget_message_video_thumb')
            style = (photo or video_thumb).get('style', '') if (photo or video_thumb) else ""
            if "url('" in style: media_url = style.split("url('")[1].split("')")[0]
            posts.append({
                'id': f"{channel_name}_{link_area.get('href').split('/')[-1]}",
                'full_name': full_name,
                'content': content_html,
                'text_plain': text_area.get_text(separator=' '),
                'date_raw': date_area.get('datetime') if date_area else '',
                'link': link_area.get('href'),
                'handle': channel_name,
                'media': media_url,
                'video': video_url
            })
    except: pass
    return posts

# ==========================================
# 3. ОСНОВНОЙ ПРОЦЕСС
# ==========================================

def aggregate():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            try: archive = json.load(f)
            except: archive = []
    else: archive = []

    all_current = []
    for ch in DISPLAY_CHANNELS:
        all_current.extend(get_tg_posts(ch))
    
    ai_data = {
        "escalation": "??%", "nuclear_risk": "??%", "ground_op": "??%", "iran_chance": "??%", 
        "forecast_date": "анализ...", "analysis": "Сбор данных...", "rumors_block": "Мониторинг..."
    }

    if model:
        context_text = " ".join([p['text_plain'] for p in all_current[:40]])
        oil = get_oil_price()
        rumors = get_reddit_rumors()
        prompt = f"Analyze news: {context_text[:6000]}. Oil: {oil}. Rumors: {rumors}. Return ONLY JSON: {{\"escalation\":\"X%\",\"nuclear_risk\":\"X%\",\"ground_op\":\"X%\",\"iran_chance\":\"X%\",\"forecast_date\":\"DD.MM\",\"analysis\":\"12 sentences\",\"rumors_block\":\"10 sentences\"}}"
        try:
            res = model.generate_content(prompt)
            json_match = re.search(r'\{.*\}', res.text, re.DOTALL)
            if json_match:
                ai_data = json.loads(json_match.group())
        except Exception as e:
            print(f"AI Error: {e}")

    existing_ids = {p['id'] for p in archive}
    for np in all_current:
        if np['id'] not in existing_ids: archive.append(np)
    archive.sort(key=lambda x: x.get('date_raw', ''), reverse=True)
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive[:1500], f, ensure_ascii=False, indent=2)

    # ИСПРАВЛЕНО: Время сборки по Москве (UTC+3)
    build_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).strftime("%H:%M")

    html_template = """<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>Intelligence Center</title>
    <style>
        :root { --bg: #f2f2f7; --card: #ffffff; --text: #000; --accent: #007aff; }
        [data-theme="dark"] { --bg: #000; --card: #1c1c1e; --text: #fff; --accent: #0a84ff; }
        body { background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; margin: 0; padding-bottom: 100px; }
        header { position: sticky; top: 0; z-index: 1000; background: rgba(255,255,255,0.8); backdrop-filter: blur(20px); padding: 15px 20px; border-bottom: 0.5px solid rgba(0,0,0,0.1); display:flex; justify-content:space-between; align-items:center; }
        [data-theme="dark"] header { background: rgba(0,0,0,0.8); }
        .summary-card { background: var(--card); border-radius: 25px; padding: 25px; margin: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .stat-box { background: rgba(120,120,128,0.08); padding: 12px; border-radius: 15px; font-size: 11px; font-weight: 600; display: flex; flex-direction: column; }
        .stat-val { font-size: 18px; font-weight: 800; color: var(--accent); margin-top: 5px; }
        .card { background: var(--card); border-radius: 20px; padding: 20px; margin: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); overflow: hidden; }
        .media-container { width: calc(100% + 40px); margin: -20px -20px 15px -20px; background: #000; }
        .media-img, video { width: 100%; display: block; max-height: 80vh; object-fit: contain; }
        .tabs { position: fixed; bottom: 0; width: 100%; background: var(--card); display: flex; padding: 12px 0 35px 0; border-top: 0.5px solid rgba(0,0,0,0.1); }
        .tab { flex: 1; text-align: center; text-decoration: none; color: #8e8e93; font-size: 10px; font-weight: 700; }
        .tab.active { color: var(--accent); }
        .post-time { opacity: 0.6; font-size: 13px; font-weight: 700; background: rgba(120,120,128,0.12); padding: 4px 10px; border-radius: 10px; }
    </style>
</head>
<body>
<header>
    <h1 style="margin:0; font-size:24px; font-weight:900;">Intelligence</h1>
    <button onclick="toggleTheme()" style="background:none; border:none; font-size:20px;">🌓</button>
</header>
<div style="max-width:600px; margin: 0 auto;">
    <div class="summary-card">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:20px;">
            <h2 style="margin:0; font-size:16px; font-weight:900;">STRATEGIC AI SUMMARY <span style="background:var(--accent); color:#fff; padding:2px 6px; border-radius:4px; font-size:9px;">G3</span></h2>
            <span style="font-size:15px; font-weight:900; color:var(--accent);">_TIME_ MSK</span>
        </div>
        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">_ESC_</span></div>
            <div class="stat-box">Ядерный удар<span class="stat-val">_NUC_</span></div>
            <div class="stat-box">Наземная операция<span class="stat-val">_GND_</span></div>
            <div class="stat-box">Шанс Ирана<span class="stat-val">_IRAN_</span></div>
            <div class="stat-box" style="grid-column: span 2; border: 1px solid rgba(0,122,255,0.2); flex-direction:row; align-items:center; justify-content:space-between; padding:15px;">
                Прогноз начала наземной операции: <span class="stat-val" style="margin:0;">_DATE_</span>
            </div>
        </div>
        <div style="margin-top:20px;">
            <div style="font-size:15px; line-height:1.6; opacity:0.9;">_ANALYSIS_</div>
            <div style="margin-top:20px; padding:15px; background:rgba(255,149,0,0.08); border-left:4px solid #ff9500; border-radius:10px;">
                <strong style="color:#ff9500; font-size:12px;">СЛУХИ И СОЦСЕТИ:</strong><br>
                <div style="margin-top:5px;">_RUMORS_</div>
            </div>
        </div>
    </div>
    <div id="feed"></div>
</div>
<div class="tabs">
    <a href="#" class="tab active" onclick="render('all')">📰 СВОДКА</a>
    <a href="#" class="tab" onclick="render('archive')">📦 АРХИВ</a>
    <a href="#" class="tab" onclick="render('fav')">⭐ SAVED</a>
</div>
<script>
    const allPosts = _JSON_DATA_;
    function toggleTheme() {
        const t = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', t);
    }
    function render(mode) {
        const container = document.getElementById('feed');
        let posts = allPosts.slice(0, 50);
        if(mode === 'archive') posts = allPosts.slice(50, 300);
        container.innerHTML = posts.map(p => {
            // ИСПРАВЛЕНО: Преобразование времени поста в московское (UTC+3)
            let mskTime = '';
            if(p.date_raw) {
                const date = new Date(p.date_raw);
                // Если браузер в другом поясе, принудительно вычисляем UTC+3
                mskTime = new Date(date.getTime() + (3 * 60 * 60 * 1000)).toISOString().split('T')[1].slice(0,5);
            }
            return `
            <div class="card">
                ${p.video ? `<video src="${p.video}" controls style="width:100%"></video>` : (p.media ? `<img src="${p.media}" style="width:100%">` : '')}
                <div style="padding:20px">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px">
                        <span style="font-weight:800; color:var(--accent)">${p.full_name}</span>
                        <span class="post-time">${mskTime}</span>
                    </div>
                    <div style="font-size:16px">${p.content}</div>
                </div>
            </div>
        `}).join('');
    }
    render('all');
</script>
</body>
</html>"""

    f_html = html_template.replace('_TIME_', build_time)
    f_html = f_html.replace('_ESC_', ai_data.get('escalation', '??%'))
    f_html = f_html.replace('_NUC_', ai_data.get('nuclear_risk', '??%'))
    f_html = f_html.replace('_GND_', ai_data.get('ground_op', '??%'))
    f_html = f_html.replace('_IRAN_', ai_data.get('iran_chance', '??%'))
    f_html = f_html.replace('_DATE_', ai_data.get('forecast_date', 'анализ...'))
    f_html = f_html.replace('_ANALYSIS_', ai_data.get('analysis', 'Нет данных'))
    f_html = f_html.replace('_RUMORS_', ai_data.get('rumors_block', 'Нет данных'))
    f_html = f_html.replace('_JSON_DATA_', json.dumps(archive, ensure_ascii=False))

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f_html)

if __name__ == "__main__":
    aggregate()
