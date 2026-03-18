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

# Каналы, которые ОТОБРАЖАЮТСЯ в ленте на сайте
DISPLAY_CHANNELS = [
    'chirpnews', 'condottieros', 'infantmilitario', 
    'victorstepanych', 'varlamov_news'
]

# Каналы только для АНАЛИЗА (Иран, OSINT, агрегаторы X)
ANALYSIS_CHANNELS = [
    'tasnim_khabar', 'farsna', 'Military_Arabic', 
    'intelsky', 'war_monitor'
]

# Мировые СМИ (RSS)
RSS_FEEDS = [
    'https://www.aljazeera.com/xml/rss/all.xml',
    'https://www.timesofisrael.com/feed/',
    'https://news.google.com/rss/search?q=Associated+Press+Middle+East&hl=en-US'
]

ARCHIVE_FILE = 'archive.json'
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Настройка Gemini 3 (актуальная модель на март 2026)
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    # Используем gemini-3-pro для максимально глубокого анализа
    model = genai.GenerativeModel('gemini-3-pro')
else:
    model = None

# ==========================================
# 2. ВСПОМОГАТЕЛЬНЫЕ СКРИПТЫ СБОРА
# ==========================================

def get_oil_price():
    """Получение текущей цены на нефть Brent"""
    try:
        oil = yf.Ticker("BZ=F") 
        price = oil.history(period='1d')['Close'].iloc[-1]
        return f"{price:.2f}"
    except: return "92.50"

def get_reddit_rumors():
    """Сбор заголовков из Reddit для анализа слухов"""
    rumors = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get("https://www.reddit.com/r/MiddleEastNews/new.json?limit=15", headers=headers, timeout=10)
        data = res.json()
        for post in data['data']['children']:
            rumors.append(post['data']['title'])
    except: pass
    return " | ".join(rumors)

def get_tg_posts(channel_name, limit=30):
    """Парсинг постов из Telegram"""
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
            
            # Медиа: Видео или Фото
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
                'handle': channel_name,
                'media': img,
                'video': video_url
            })
    except: pass
    return posts

# ==========================================
# 3. ГЛАВНАЯ ЛОГИКА АГРЕГАЦИИ И АНАЛИЗА
# ==========================================

def aggregate():
    # 1. Собираем посты для ленты (карточки под таблицей)
    feed_posts = []
    for ch in DISPLAY_CHANNELS:
        feed_posts.extend(get_tg_posts(ch, limit=40))
    
    # 2. Собираем контекст для ИИ (50 постов из ленты + 10 из каждого иранского канала)
    # Берем именно 50 последних постов из тех, что пойдут в ленту
    feed_posts_sorted = sorted(feed_posts, key=lambda x: x['date_raw'], reverse=True)
    ai_context = "НОВОСТИ ИЗ ОСНОВНОЙ ЛЕНТЫ:\n"
    ai_context += " ".join([p['text_plain'] for p in feed_posts_sorted[:50]])
    
    ai_context += "\nДАННЫЕ ИЗ ИРАНСКИХ И OSINT ИСТОЧНИКОВ:\n"
    for ch in ANALYSIS_CHANNELS:
        extra_posts = get_tg_posts(ch, limit=15)
        ai_context += " " + " ".join([p['text_plain'] for p in extra_posts])
    
    ai_context += "\nМИРОВЫЕ СМИ (RSS):\n"
    for url in RSS_FEEDS:
        try:
            f = feedparser.parse(url)
            ai_context += " " + " ".join([e.title for e in f.entries[:5]])
        except: pass

    # 3. Анализ через Gemini 3
    ai_data = {
        "escalation": "??%", "nuclear_risk": "??%", "ground_op": "??%", "forecast_date": "анализ...",
        "analysis": "Система Gemini 3 обрабатывает данные...", 
        "rumors_block": "Мониторинг X и Reddit в процессе..."
    }

    if model:
        oil_info = get_oil_price()
        rumors_info = get_reddit_rumors()
        
        prompt = f"""
        Ты — ведущий аналитик геополитической разведки. Твоя задача — провести синтез данных.
        
        КОНТЕКСТ (50 постов ленты + Иран + СМИ): {ai_context}
        СЛУХИ И СОЦСЕТИ: {rumors_info}
        ЭКОНОМИКА (Цена Brent): {oil_info}
        
        На основе этих данных сформируй отчет. 
        ОТВЕТЬ СТРОГО В ФОРМАТЕ JSON:
        {{
          "escalation": "число%", 
          "nuclear_risk": "число%", 
          "ground_op": "число%", 
          "forecast_date": "дд.мм",
          "analysis": "ровно 12 предложений глубокого стратегического анализа ситуации.",
          "rumors_block": "ровно 12 предложений анализа неподтвержденных слухов, настроений в X и Reddit."
        }}
        """
        try:
            response = model.generate_content(prompt)
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                ai_data = json.loads(json_match.group())
        except Exception as e:
            print(f"AI Error: {e}")

    # 4. Обновление архива (DISPLAY_CHANNELS только)
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

    # 5. Формирование HTML
    now_msk = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).strftime("%H:%M")
    
    html_template = f'''<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>Intelligence Center v3.0</title>
    <style>
        :root {{ --bg: #f2f2f7; --card: #ffffff; --text: #000; --accent: #007aff; --rumor: #ff9500; }}
        [data-theme="dark"] {{ --bg: #000; --card: #1c1c1e; --text: #fff; --accent: #0a84ff; --rumor: #ff9f0a; }}
        body {{ background: var(--bg); color: var(--text); font-family: -apple-system, system-ui, sans-serif; margin: 0; padding-bottom: 100px; -webkit-font-smoothing: antialiased; }}
        header {{ position: sticky; top: 0; z-index: 1000; background: rgba(255,255,255,0.8); backdrop-filter: blur(20px); padding: 15px 20px; border-bottom: 0.5px solid rgba(0,0,0,0.1); display:flex; justify-content:space-between; align-items:center; }}
        [data-theme="dark"] header {{ background: rgba(0,0,0,0.8); }}
        .summary-card {{ background: var(--card); border-radius: 25px; padding: 25px; margin: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.03); }}
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .stat-box {{ background: rgba(120,120,128,0.08); padding: 12px; border-radius: 15px; font-size: 11px; font-weight: 600; display: flex; flex-direction: column; }}
        .stat-val {{ font-size: 19px; font-weight: 900; color: var(--accent); margin-top: 5px; }}
        .card {{ background: var(--card); border-radius: 22px; padding: 20px; margin: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); overflow: hidden; position: relative; border: 0.5px solid rgba(0,0,0,0.05); }}
        .media-container {{ width: calc(100% + 40px); margin: -20px -20px 15px -20px; background: #000; }}
        .media-img, video {{ width: 100%; display: block; max-height: 75vh; object-fit: contain; }}
        .content {{ line-height: 1.55; font-size: 16px; word-wrap: break-word; }}
        .rumors-section {{ margin-top:20px; padding:15px; background:rgba(255,149,0,0.08); border-left:4px solid var(--rumor); border-radius:12px; font-size:14px; line-height:1.6; color: var(--text); }}
        .tabs {{ position: fixed; bottom: 0; width: 100%; background: var(--card); display: flex; padding: 12px 0 35px 0; border-top: 0.5px solid rgba(0,0,0,0.1); z-index: 1000; }}
        .tab {{ flex: 1; text-align: center; text-decoration: none; color: #8e8e93; font-size: 10px; font-weight: 700; text-transform: uppercase; }}
        .tab.active {{ color: var(--accent); }}
        .badge-ai {{ background: var(--accent); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 9px; vertical-align: middle; margin-left: 5px; }}
    </style>
</head>
<body>
<header>
    <h1 style="margin:0; font-size:22px; font-weight:900; letter-spacing:-0.5px;">Intelligence</h1>
    <button onclick="toggleTheme()" style="background:none; border:none; font-size:20px; cursor:pointer;">🌓</button>
</header>
<div id="main-content" style="max-width:600px; margin: 0 auto;">
    <div class="summary-card">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:20px; border-bottom:1px solid rgba(0,0,0,0.1); padding-bottom:10px;">
            <h2 style="margin:0; font-size:16px; font-weight:900; text-transform:uppercase;">Strategic AI Summary <span class="badge-ai">G3</span></h2>
            <span style="font-size:14px; font-weight:900; color:var(--accent);">{now_msk} MSK</span>
        </div>
        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">{ai_data['escalation']}</span></div>
            <div class="stat-box">Ядерный риск<span class="stat-val">{ai_data['nuclear_risk']}</span></div>
            <div class="stat-box">Наземная оп.<span class="stat-val">{ai_data['ground_op']}</span></div>
            <div class="stat-box">Прогноз даты<span class="stat-val">{ai_data['forecast_date']}</span></div>
        </div>
        <div style="margin-top:20px;">
            <h3 style="margin:0 0 10px 0; font-size:15px; font-weight:800;">Глобальный анализ ситуации</h3>
            <div style="font-size:14px; line-height:1.6; opacity:0.85;">{ai_data['analysis']}</div>
            <div class="rumors-section">
                <strong style="color:var(--rumor); text-transform:uppercase; font-size:12px;">Мониторинг слухов (X/Reddit/Forums):</strong><br>
                <div style="margin-top:5px; opacity:0.9;">{ai_data['rumors_block']}</div>
            </div>
        </div>
    </div>
    <div id="feed"></div>
</div>
<div class="tabs">
    <a href="javascript:void(0)" class="tab active" onclick="render('all', this)">📰<br>Сводка</a>
    <a href="javascript:void(0)" class="tab" onclick="render('archive', this)">📦<br>Архив</a>
    <a href="javascript:void(0)" class="tab" onclick="render('fav', this)">⭐<br>Saved</a>
</div>

<script>
    const allPosts = {json.dumps(archive[:250])};
    let favorites = JSON.parse(localStorage.getItem('favs') || '[]');
    
    function toggleTheme() {{
        const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }}

    function render(mode = 'all', el = null) {{
        if(el) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            el.classList.add('active');
        }}
        const container = document.getElementById('feed');
        let posts = mode === 'all' ? allPosts.slice(0, 50) : (mode === 'archive' ? allPosts.slice(50, 250) : allPosts.filter(p => favorites.includes(p.id)));
        
        container.innerHTML = posts.map(p => `
            <div class="card" id="card-${{p.id}}">
                ${{p.video ? `<div class="media-container"><video src="${{p.video}}" autoplay muted loop playsinline controls></video></div>` : (p.media ? `<div class="media-container"><img src="${{p.media}}" class="media-img" loading="lazy"></div>` : '')}}
                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                    <span style="font-weight:800; color:var(--accent); font-size:15px;">${{p.full_name}}</span>
                    <span style="opacity:0.4; font-size:12px; font-weight:600;">${{p.date_raw ? p.date_raw.split('T')[1].slice(0,5) : ''}}</span>
                </div>
                <div class="content">${{p.content}}</div>
                <div style="margin-top:15px; display:flex; gap:10px;">
                    <button style="background:none; border:none; cursor:pointer; font-size:22px; padding:0;" onclick="toggleFav('${{p.id}}')">
                        ${{favorites.includes(p.id)?'⭐':'☆'}}
                    </button>
                    <a href="${{p.link}}" target="_blank" style="text-decoration:none; font-size:12px; color:var(--accent); font-weight:700; align-self:center;">OPEN IN TG</a>
                </div>
            </div>
        `).join('');
    }}

    function toggleFav(id) {{
        if(favorites.includes(id)) favorites = favorites.filter(f => f !== id);
        else favorites.push(id);
        localStorage.setItem('favs', JSON.stringify(favorites));
        render();
    }}

    document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') || 'light');
    render();
</script>
</body>
</html>'''

    with open('index.html', 'w', encoding='utf-
