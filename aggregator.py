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
# 1. КОНФИГУРАЦИЯ ИСТОЧНИКОВ
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
    # Исправлено: используем стабильную модель 1.5 Pro
    model = genai.GenerativeModel('gemini-1.5-pro')
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

def get_tg_posts(channel_name, limit=100):
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
            content_html = re.sub(r'<a[^>]*tgme_widget_message_text_more[^>]*>.*?</a>', '', content_html)
            
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
            if "url('" in style: 
                media_url = style.split("url('")[1].split("')")[0]

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
    except Exception as e: 
        print(f"Error {channel_name}: {e}")
    return posts

# ==========================================
# 3. ОСНОВНОЙ ЦИКЛ
# ==========================================

def aggregate():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            try: archive = json.load(f)
            except: archive = []
    else: archive = []

    all_scraped = []
    for ch in DISPLAY_CHANNELS:
        all_scraped.extend(get_tg_posts(ch, limit=50))
    
    new_posts_sorted = sorted(all_scraped, key=lambda x: x['date_raw'], reverse=True)
    
    ai_context = "ЛЕНТА:\n" + " ".join([p['text_plain'] for p in new_posts_sorted[:50]])
    for ch in ANALYSIS_CHANNELS:
        extra = get_tg_posts(ch, limit=10)
        ai_context += " " + " ".join([p['text_plain'] for p in extra])

    ai_data = {
        "escalation": "??%", "nuclear_risk": "??%", "ground_op": "??%", "iran_chance": "??%", 
        "forecast_date": "анализ...", "analysis": "Данные обновляются...", "rumors_block": "Поиск слухов..."
    }

    if model:
        oil_info = get_oil_price()
        rumors_info = get_reddit_rumors()
        prompt = f"Data: {ai_context[:6000]}. Oil: {oil_info}. Rumors: {rumors_info}. Return ONLY JSON: {{'escalation': 'X%', 'nuclear_risk': 'X%', 'ground_op': 'X%', 'iran_chance': 'X%', 'forecast_date': 'DD.MM', 'analysis': '12 sentences', 'rumors_block': '10 sentences'}}"
        try:
            response = model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group().replace("'", '"'))
        except Exception as e:
            print(f"AI Error: {e}")

    # Сохраняем архив
    existing_ids = {p['id'] for p in archive}
    for np in all_scraped:
        if np['id'] not in existing_ids: archive.append(np)
    archive.sort(key=lambda x: x.get('date_raw', ''), reverse=True)
    
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive[:2000], f, ensure_ascii=False, indent=2)

    # Время (исправлено название переменной)
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
        .tabs { position: fixed; bottom: 0; width: 100%; background: var(--card); display: flex; padding: 12px 0 35px 0; border-top: 0.5px solid rgba(0,0,0,0.1); z-index: 1000; }
        .tab { flex: 1; text-align: center; text-decoration: none; color: #8e8e93; font-size: 10px; font-weight: 700; }
        .tab.active { color: var(--accent); }
        .refresh-btn { background: var(--accent); color: white; border: none; padding: 10px 16px; border-radius: 12px; font-size: 11px; font-weight: 800; cursor: pointer; }
        .rumors-section { margin-top:15px; padding:15px; background:rgba(255,149,0,0.08); border-left:4px solid #ff9500; border-radius:12px; font-size:14px; }
    </style>
</head>
<body>
<header>
    <h1 style="margin:0; font-size:24px; font-weight:900;">Intelligence</h1>
    <button onclick="toggleTheme()" style="background:none; border:none; font-size:20px;">🌓</button>
</header>
<div style="max-width:600px; margin: 0 auto;">
    <div class="summary-card">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:20px; border-bottom:1px solid rgba(0,0,0,0.1); padding-bottom:10px;">
            <h2 style="margin:0; font-size:16px; font-weight:900;">STRATEGIC AI SUMMARY</h2>
            <span style="font-size:15px; font-weight:900; color:var(--accent);">_TIME_ MSK</span>
        </div>
        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">_ESC_</span></div>
            <div class="stat-box">Ядерный риск<span class="stat-val">_NUC_</span></div>
            <div class="stat-box">Наземная операция<span class="stat-val">_GND_</span></div>
            <div class="stat-box">Шанс Ирана<span class="stat-val">_IRAN_</span></div>
            <div class="stat-box" style="grid-column: span 2; border: 1px solid rgba(0,122,255,0.2); flex-direction:row; align-items:center; justify-content:space-between; padding: 15px;">
                Прогноз начала наземной операции: <span class="stat-val" style="margin:0;">_DATE_</span>
            </div>
        </div>
        <div style="margin-top:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <h3 style="margin:0; font-size:16px;">Глобальный анализ</h3>
                <button onclick="location.reload()" class="refresh-btn">REFRESH</button>
            </div>
            <div style="line-height:1.6; font-size:15px; opacity:0.9;">_ANALYSIS_</div>
            <div class="rumors-section">
                <strong style="color:#ff9500; font-size:12px;">СЛУХИ И СОЦСЕТИ:</strong><br>
                <div style="margin-top:5px;">_RUMORS_</div>
            </div>
        </div>
    </div>
    <div id="feed"></div>
</div>
<div class="tabs">
    <a href="javascript:void(0)" class="tab active" onclick="render('all', this)">📰 СВОДКА</a>
    <a href="javascript:void(0)" class="tab" onclick="render('archive', this)">📦 АРХИВ</a>
    <a href="javascript:void(0)" class="tab" onclick="render('fav', this)">⭐ SAVED</a>
</div>
<script>
    const allPosts = _JSON_DATA_;
    let favorites = JSON.parse(localStorage.getItem('favs') || '[]');
    function toggleTheme() {
        const t = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', t);
        localStorage.setItem('theme', t);
    }
    function render(mode = 'all', el = null) {
        if(el) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            el.classList.add('active');
        }
        const container = document.getElementById('feed');
        let posts = mode === 'all' ? allPosts.slice(0, 50) : (mode === 'archive' ? allPosts.slice(50, 500) : allPosts.filter(p => favorites.includes(p.id)));
        container.innerHTML = posts.map(p => `
            <div class="card" id="card-${p.id}">
                ${p.video ? `<div class="media-container"><video src="${p.video}" autoplay muted loop playsinline controls></video></div>` : (p.media ? `<div class="media-container"><img src="${p.media}"></div>` : '')}
                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                    <span style="font-weight:800; color:var(--accent);">${p.full_name}</span>
                    <span style="opacity:0.4; font-size:12px;">${p.date_raw.split('T')[1]?.slice(0,5) || ''}</span>
                </div>
                <div style="font-size:16px; line-height:1.5;">${p.content}</div>
                <button style="background:none; border:none; cursor:pointer; font-size:24px; margin-top:10px;" onclick="toggleFav('${p.id}')">${favorites.includes(p.id)?'⭐':'☆'}</button>
            </div>
        `).join('');
        initVideoObserver();
    }
    function toggleFav(id) {
        if(favorites.includes(id)) favorites = favorites.filter(f => f !== id);
        else favorites.push(id);
        localStorage.setItem('favs', JSON.stringify(favorites));
        render(window.currentMode || 'all');
    }
    function initVideoObserver() {
        const obs = new IntersectionObserver((es) => {
            es.forEach(e => { if(e.isIntersecting) e.target.play().catch(()=>{}); else e.target.pause(); });
        }, { threshold: 0.5 });
        document.querySelectorAll('video').forEach(v => obs.observe(v));
    }
    document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') || 'light');
    render();
</script>
</body>
</html>"""

    # Безопасная вставка данных
    f_html = html_template.replace('_TIME_', build_time)
    f_html = f_html.replace('_ESC_', ai_data['escalation'])
    f_html = f_html.replace('_NUC_', ai_data['nuclear_risk'])
    f_html = f_html.replace('_GND_', ai_data['ground_op'])
    f_html = f_html.replace('_IRAN_', ai_data['iran_chance'])
    f_html = f_html.replace('_DATE_', ai_data['forecast_date'])
    f_html = f_html.replace('_ANALYSIS_', ai_data['analysis'])
    f_html = f_html.replace('_RUMORS_', ai_data['rumors_block'])
    f_html = f_html.replace('_JSON_DATA_', json.dumps(archive, ensure_ascii=False))

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f_html)

if __name__ == "__main__":
    aggregate()
