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
    # Используем Gemini 3 Pro (март 2026)
    model = genai.GenerativeModel('gemini-3-pro')
else:
    model = None

# ==========================================
# 2. ФУНКЦИИ СБОРА
# ==========================================

def get_oil_price():
    try:
        oil = yf.Ticker("BZ=F") 
        return f"{oil.history(period='1d')['Close'].iloc[-1]:.2f}"
    except: return "92.50"

def get_reddit_rumors():
    rumors = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get("https://www.reddit.com/r/MiddleEastNews/new.json?limit=15", headers=headers, timeout=10)
        for post in res.json()['data']['children']:
            rumors.append(post['data']['title'])
    except: pass
    return " | ".join(rumors)

def get_tg_posts(channel_name, limit=100):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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
            
            # Возвращаем твою качественную очистку HTML!
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
    # 1. Загружаем архив
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            try: archive = json.load(f)
            except: archive = []
    else: archive = []

    # 2. Собираем новые посты ленты
    new_posts = []
    for ch in DISPLAY_CHANNELS:
        new_posts.extend(get_tg_posts(ch, limit=50))
    
    # Сортируем новые посты по дате (свежие сверху) для ИИ
    new_posts_sorted = sorted(new_posts, key=lambda x: x['date_raw'] if x.get('date_raw') else "", reverse=True)
    
    # 3. Собираем контекст ИИ (берем 50 последних постов из ленты + скрытые каналы)
    ai_context = "ЛЕНТА (50 постов):\n" + " ".join([p['text_plain'] for p in new_posts_sorted[:50]])
    ai_context += "\nИРАН/OSINT:\n"
    for ch in ANALYSIS_CHANNELS:
        extra_posts = get_tg_posts(ch, limit=15)
        ai_context += " " + " ".join([p['text_plain'] for p in extra_posts])
    
    ai_context += "\nRSS:\n"
    for url in RSS_FEEDS:
        try:
            f = feedparser.parse(url)
            ai_context += " " + " ".join([e.title for e in f.entries[:5]])
        except: pass

    # 4. Анализ ИИ (Gemini 3 Pro)
    # Настраиваем ключи JSON под твою сетку в HTML
    ai_data = {
        "escalation": "??%", "nuclear_risk": "??%", "ground_op": "??%", "iran_chance": "??%", 
        "forecast_date": "Анализ...",
        "analysis": "Gemini 3 Pro собирает данные...", 
        "rumors_block": "Мониторинг X/Reddit..."
    }

    if model:
        oil_info = get_oil_price()
        rumors_info = get_reddit_rumors()
        prompt = f"""
        Проанализируй данные геополитической разведки. 
        Контекст: {ai_context[:6000]}
        Слухи: {rumors_info}
        Нефть: {oil_info}
        
        Верни СТРОГО JSON:
        {{
          "escalation": "число%", "nuclear_risk": "число%", "ground_op": "число%", "iran_chance": "число%", 
          "forecast_date": "дд.мм",
          "analysis": "12 предложений глобального анализа (включая экономику и нефть).",
          "rumors_block": "Анализ слухов (5 предложений)."
        }}
        """
        try:
            response = model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                ai_data = json.loads(match.group().replace("'", '"'))
        except Exception as e:
            print(f"AI Error: {e}")

    # 5. Сохранение архива (возвращаем лимит 2000)
    existing_ids = {p['id'] for p in archive}
    for np in new_posts:
        if np['id'] not in existing_ids: archive.append(np)
    
    archive.sort(key=lambda x: x.get('date_raw', ''), reverse=True)
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive[:2000], f, ensure_ascii=False, indent=2)

    # 6. ГЕНЕРАЦИЯ HTML
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_msk = now_utc + datetime.timedelta(hours=3)
    build_time = now_msk.strftime("%H:%M")

    # Безопасный HTML-шаблон (без f-строк)
    html_template = """<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>Intelligence Center</title>
    <style>
        :root { --bg: #f2f2f7; --card: #ffffff; --text: #000; --accent: #007aff; }
        [data-theme="dark"] { --bg: #000; --card: #1c1c1e; --text: #fff; --accent: #0a84ff; }
        body { background: var(--bg); color: var(--text); font-family: -apple-system, system-ui, sans-serif; margin: 0; padding-bottom: 100px; -webkit-tap-highlight-color: transparent; }
        header { position: sticky; top: 0; z-index: 1000; background: rgba(255,255,255,0.8); backdrop-filter: blur(20px); padding: 15px 20px; border-bottom: 0.5px solid rgba(0,0,0,0.1); display:flex; justify-content:space-between; align-items:center; }
        [data-theme="dark"] header { background: rgba(0,0,0,0.8); }
        .summary-card { background: var(--card); border-radius: 25px; padding: 25px; margin: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .stat-box { background: rgba(120,120,128,0.08); padding: 12px; border-radius: 15px; font-size: 11px; font-weight: 600; display: flex; flex-direction: column; }
        .stat-val { font-size: 18px; font-weight: 800; color: var(--accent); margin-top: 5px; }
        .card { background: var(--card); border-radius: 20px; padding: 20px; margin: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); overflow: hidden; position: relative; }
        .media-container { width: calc(100% + 40px); margin: -20px -20px 15px -20px; background: #000; }
        .media-img, video { width: 100%; display: block; max-height: 80vh; object-fit: contain; }
        .content { line-height: 1.5; font-size: 16px; word-wrap: break-word; }
        .tabs { position: fixed; bottom: 0; width: 100%; background: var(--card); display: flex; padding: 12px 0 35px 0; border-top: 0.5px solid rgba(0,0,0,0.1); z-index: 1000; }
        .tab { flex: 1; text-align: center; text-decoration: none; color: #8e8e93; font-size: 10px; font-weight: 700; }
        .tab.active { color: var(--accent); }
        .refresh-btn { background: var(--accent); color: white; border: none; padding: 10px 16px; border-radius: 12px; font-size: 11px; font-weight: 800; cursor: pointer; transition: transform 0.1s; }
        .refresh-btn:active { transform: scale(0.95); opacity: 0.8; }
        .badge-ai { background: var(--accent); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 9px; vertical-align: middle; margin-left: 5px; }
        .rumors-section { margin-top:15px; padding:15px; background:rgba(255,149,0,0.08); border-left:4px solid #ff9500; border-radius:12px; font-size:14px; line-height:1.6; }
    </style>
</head>
<body>
<header>
    <h1 style="margin:0; font-size:24px; font-weight:900;">Intelligence</h1>
    <button onclick="toggleTheme()" style="background:none; border:none; font-size:20px; cursor:pointer;">🌓</button>
</header>
<div id="main-content" style="max-width:600px; margin: 0 auto;">
    
    <div class="summary-card">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:20px; border-bottom:1px solid rgba(0,0,0,0.1); padding-bottom:10px;">
            <h2 style="margin:0; font-size:16px; letter-spacing:-0.5px; font-weight:900;">STRATEGIC AI SUMMARY <span class="badge-ai">G3</span></h2>
            <div style="text-align:right">
                <span style="font-size:11px; opacity:0.5; display:block; font-weight:700;">LAST UPDATE</span>
                <span style="font-size:15px; font-weight:900; color:var(--accent);">__TIME__ MSK</span>
            </div>
        </div>

        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">__ESC__</span></div>
            <div class="stat-box">Ядерный удар<span class="stat-val">__NUC__</span></div>
            <div class="stat-box">Наземная операция<span class="stat-val">__GND__</span></div>
            <div class="stat-box">Шанс Ирана<span class="stat-val">__IRAN__</span></div>
            <div class="stat-box" style="grid-column: span 2; border: 1px solid rgba(0,122,255,0.2); flex-direction:row; align-items:center; justify-content:space-between;">
                Прогноз начала наземной операции: <span class="stat-val" style="margin:0; color:var(--accent);">__DATE__</span>
            </div>
        </div>

        <div class="ai-text-block" style="margin-top:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <h3 style="margin:0; font-size:16px;">Глобальный анализ ситуации</h3>
                <button onclick="location.reload()" class="refresh-btn">REFRESH PAGE</button>
            </div>
            <div class="summary-section" style="line-height:1.6; font-size:15px; opacity:0.9;">
                __ANALYSIS__
            </div>
            <div class="rumors-section">
                <strong style="color:#ff9500; font-size:12px; text-transform:uppercase;">Слухи и соцсети (X / Reddit):</strong><br>
                <div style="margin-top:5px; opacity:0.9;">__RUMORS__</div>
            </div>
        </div>
    </div>

    <div id="feed"></div>
</div>
<div class="tabs">
    <a href="javascript:void(0)" class="tab active" onclick="render('all', this)">📰<br>СВОДКА</a>
    <a href="javascript:void(0)" class="tab" onclick="render('archive', this)">📦<br>АРХИВ</a>
    <a href="javascript:void(0)" class="tab" onclick="render('fav', this)">⭐<br>SAVED</a>
</div>

<script>
    const allPosts = __JSON_ARCHIVE__;
    let favorites = JSON.parse(localStorage.getItem('favs') || '[]');
    let currentMode = 'all';

    function formatDeviceTime(rawDate) {
        if(!rawDate) return '';
        const d = new Date(rawDate);
        return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    }

    function toggleTheme() {
        const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }

    function render(mode = 'all', el = null) {
        currentMode = mode;
        if(el) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            el.classList.add('active');
        }
        const container = document.getElementById('feed');
        let html = '';
        
        let posts = [];
        if(mode === 'all') posts = allPosts.slice(0, 50);
        else if(mode === 'archive') posts = allPosts.slice(50, 500);
        else posts = allPosts.filter(p => favorites.includes(p.id));
        
        posts.forEach(p => {
            const isFav = favorites.includes(p.id);
            let mediaHtml = p.video 
                ? `<div class="media-container"><video src="${p.video}" autoplay muted loop playsinline controls preload="metadata"></video></div>`
                : (p.media ? `<div class="media-container"><img src="${p.media}" class="media-img" loading="lazy"></div>` : '');

            html += `<div class="card" id="card-${p.id}">
                ${mediaHtml}
                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                    <a href="${p.link}" target="_blank" style="font-weight:800; color:var(--accent); text-decoration:none;">
                        ${p.full_name}<br><span style="opacity:0.5; font-size:12px; font-weight:400;">@${p.handle}</span>
                    </a>
                    <span style="opacity:0.4; font-size:12px; font-weight:700;">${formatDeviceTime(p.date_raw)}</span>
                </div>
                <div class="content">${p.content}</div>
                <div style="margin-top:15px; border-top:1px solid rgba(0,0,0,0.05); padding-top:10px;">
                    <button id="btn-${p.id}" style="background:none; border:none; cursor:pointer; font-size:24px;" onclick="toggleFav('${p.id}')">${isFav?'⭐':'☆'}</button>
                </div>
            </div>`;
        });
        container.innerHTML = html;
        initVideoObserver();
    }

    function toggleFav(id) {
        const btn = document.getElementById('btn-' + id);
        if(favorites.includes(id)) {
            favorites = favorites.filter(f => f !== id);
            btn.innerText = '☆';
            if(currentMode === 'fav') {
                document.getElementById('card-' + id).style.display = 'none';
            }
        } else {
            favorites.push(id);
            btn.innerText = '⭐';
        }
        localStorage.setItem('favs', JSON.stringify(favorites));
    }

    function initVideoObserver() {
        const options = { threshold: 0.5 };
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const video = entry.target;
                if (entry.isIntersecting) {
                    video.play().catch(() => {});
                } else {
                    video.pause();
                }
            });
        }, options);
        document.querySelectorAll('video').forEach(v => observer.observe(v));
    }

    document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') || 'light');
    render();
</script>
</body>
</html>"""

    # Подставляем данные в строку
    final_html = html_template.replace('__TIME__', build_time)
    final_html = final_html.replace('__ESC__', str(ai_data.get('escalation', '??%')))
    final_html = final_html.replace('__NUC__', str(ai_data.get('nuclear_risk', '??%')))
    final_html = final_html.replace('__GND__', str(ai_data.get('ground_op', '??%')))
    final_html = final_html.replace('__IRAN__', str(ai_data.get('iran_chance', '??%')))
    final_html = final_html.replace('__DATE__', str(ai_data.get('forecast_date', '--.--')))
    final_html = final_html.replace('__ANALYSIS__', str(ai_data.get('analysis', '')))
    final_html = final_html.replace('__RUMORS__', str(ai_data.get('rumors_block', '')))
    
    # Вставляем дамп архива в JS
    json_dump = json.dumps(archive, ensure_ascii=False)
    final_html = final_html.replace('__JSON_ARCHIVE__', json_dump)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_html)

if __name__ == "__main__":
    aggregate()
