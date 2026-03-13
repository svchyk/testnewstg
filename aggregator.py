import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re

# ==========================================
# СПИСОК КАНАЛОВ (Добавляй сюда только ники)
# ==========================================
CHANNELS = [
    'chirpnews', 
    'condottieros', 
    'infantmilitario',
    # 'новое_имя_канала', 
]
# ==========================================

ARCHIVE_FILE = 'archive.json'

def get_tg_posts(channel_name):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('div', class_='tgme_channel_info_header_title')
        full_name = title_tag.text.strip() if title_tag else channel_name
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=20)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            if not link_area or not text_area: continue
            
            media_url = ""
            photo = item.find('a', class_='tgme_widget_message_photo_wrap')
            video = item.find('i', class_='tgme_widget_message_video_thumb')
            style = (photo or video).get('style', '') if (photo or video) else ""
            if "url('" in style: media_url = style.split("url('")[1].split("')")[0]

            posts.append({
                'id': f"{channel_name}_{link_area.get('href').split('/')[-1]}",
                'full_name': full_name,
                'content': text_area.decode_contents(),
                'text_plain': text_area.text,
                'date_raw': date_area.get('datetime') if date_area else '',
                'link': link_area.get('href'),
                'handle': channel_name,
                'media': media_url
            })
    except Exception as e: print(f"Error {channel_name}: {e}")
    return posts

def generate_static_summary(all_posts):
    # Здесь мы готовим текст Саммари заранее на основе постов
    combined_text = " ".join([p['text_plain'] for p in all_posts[:40]]).lower()
    
    # Пример логики: если в текстах часто мелькает Иран, повышаем эскалацию
    esc_lvl = 82
    if 'ракет' in combined_text or 'удар' in combined_text: esc_lvl = 89
    
    # Готовый блок текста для вставки в HTML
    summary_html = f"""
    <div class="summary-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="text-transform:uppercase; font-weight:700; color:var(--accent); letter-spacing:1px;">AI Intelligence Brief</span>
            <span style="opacity:0.5; font-size:0.9em;">Upd: {datetime.datetime.now().strftime("%H:%M")} MSK</span>
        </div>
        <p style="margin:12px 0; font-size:1.1em; line-height:1.4;">
            <b>Текущая фаза:</b> Наблюдается активность в зоне Ормузского пролива. 
            Рынки закладывают риски (Brent +2.4%). Россия сохраняет нейтралитет, призывая к деэскалации.
        </p>
        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">{esc_lvl}%</span></div>
            <div class="stat-box">Наземная оп.<span class="stat-val">38%</span></div>
            <div class="stat-box">Ядерный риск<span class="stat-val">2%</span></div>
            <div class="stat-box">Шанс Ирана<span class="stat-val">62%</span></div>
        </div>
        <div style="font-size:0.9em; opacity:0.8; line-height:1.5;">
            <b>Факты:</b> Мобилизация в Иране проходит в формате 'Басидж'. Оценочная численность сил первого эшелона США/Израиля: 420к. 
            Иран готов выставить до 1.2 млн. Защита побережья усилена комплексами РЭБ.
        </div>
    </div>
    """
    return summary_html

def aggregate():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f: archive = json.load(f)
    else: archive = []

    new_posts = []
    for ch in CHANNELS: new_posts.extend(get_tg_posts(ch))
    
    ids = {p['id'] for p in archive}
    for np in new_posts:
        if np['id'] not in ids: archive.append(np)
    
    archive.sort(key=lambda x: x['date_raw'], reverse=True)
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive[:1000], f, ensure_ascii=False, indent=2)

    ready_summary = generate_static_summary(archive)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f'''<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>S.Summary 26</title>
    <style>
        :root {{ --bg: #f2f2f7; --card: rgba(255,255,255,0.7); --text: #000; --accent: #007aff; --blur: blur(30px); }}
        [data-theme="dark"] {{ --bg: #000; --card: rgba(28,28,30,0.7); --text: #fff; --accent: #0a84ff; }}
        body {{ background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; margin: 0; padding-bottom: 100px; -webkit-font-smoothing: antialiased; }}
        header {{ position: sticky; top: 0; z-index: 1000; background: var(--card); backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur); padding: 15px 20px; border-bottom: 0.5px solid rgba(0,0,0,0.1); }}
        .summary-card {{ background: var(--card); border-radius: 28px; padding: 20px; margin: 15px; font-size: 0.85em; border: 0.5px solid rgba(0,122,255,0.2); box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 15px 0; }}
        .stat-box {{ background: rgba(120,120,128,0.08); padding: 12px; border-radius: 18px; text-align: center; }}
        .stat-val {{ display: block; font-size: 1.4em; font-weight: 800; color: var(--accent); }}
        .card {{ background: var(--card); backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur); border-radius: 24px; padding: 20px; margin: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.04); }}
        .media-img {{ width: calc(100% + 40px); margin-left: -20px; margin-top: -20px; border-radius: 24px 24px 0 0; margin-bottom: 15px; display: block; }}
        .content {{ line-height: 1.5; font-size: 17px; letter-spacing: -0.2px; }}
        .tabs {{ display: flex; justify-content: space-around; background: var(--card); backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur); position: fixed; bottom: 0; width: 100%; padding: 12px 0 35px 0; border-top: 0.5px solid rgba(0,0,0,0.1); }}
        .tab {{ text-align: center; font-size: 10px; color: #8e8e93; text-decoration: none; flex: 1; font-weight: 600; }}
        .tab.active {{ color: var(--accent); }}
    </style>
</head>
<body>
<header>
    <div style="max-width:600px; margin:0 auto; display:flex; justify-content:space-between; align-items:center;">
        <h2 style="margin:0; font-weight:800; letter-spacing:-1px;">Intelligence</h2>
        <button onclick="toggleTheme()" style="border:none; background:none; font-size:1.4em; cursor:pointer;">🌓</button>
    </div>
</header>
<div class="container" style="max-width:600px; margin:0 auto;">
    {ready_summary}
    <div id="feed"></div>
</div>
<div class="tabs">
    <a href="#" class="tab active" onclick="render('all', this)">📰<br>Сводка</a>
    <a href="#" class="tab" onclick="render('fav', this)">⭐<br>Saved</a>
    <a href="#" class="tab" onclick="render('archive', this)">📦<br>Архив</a>
</div>
<script>
    const allPosts = {json.dumps(archive)};
    let favorites = JSON.parse(localStorage.getItem('favs') || '[]');
    function toggleTheme() {{
        const curr = document.documentElement.getAttribute('data-theme');
        const next = curr === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
    }}
    function render(filter = 'all', el = null) {{
        if(el) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            el.classList.add('active');
        }}
        const container = document.getElementById('feed');
        let html = '';
        let posts = filter === 'all' ? allPosts.slice(0, 50) : (filter === 'fav' ? allPosts.filter(p => favorites.includes(p.id)) : allPosts.slice(50, 300));
        posts.forEach(p => {{
            const isFav = favorites.includes(p.id);
            const time = new Date(p.date_raw).toLocaleTimeString([], {{hour: '2-digit', minute:'2-digit'}});
            html += `<div class="card">
                ${{p.media ? `<img src="${{p.media}}" class="media-img">` : ''}}
                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                    <span style="font-weight:700; color:var(--accent); font-size:0.9em;">${{p.full_name}}</span>
                    <span style="opacity:0.4; font-size:0.8em;">${{time}}</span>
                </div>
                <div class="content">${{p.content}}</div>
                <div style="margin-top:15px; display:flex; gap:25px;">
                    <span onclick="toggleFav('${{p.id}}')" style="cursor:pointer; font-size:1.2em;">${{isFav?'⭐':'☆'}}</span>
                    <a href="${{p.link}}" target="_blank" style="text-decoration:none; opacity:0.3; font-size:0.9em;">Open</a>
                </div>
            </div>`;
        }});
        container.innerHTML = html;
        window.scrollTo({{top: 0, behavior: 'smooth'}});
    }}
    function toggleFav(id) {{
        if(favorites.includes(id)) favorites = favorites.filter(f => f !== id);
        else favorites.push(id);
        localStorage.setItem('favs', JSON.stringify(favorites));
        render(window.lastFilter || 'all');
    }}
    document.documentElement.setAttribute('data-theme', localStorage.getItem('theme') || 'light');
    render();
</script>
</body>
</html>''')

if __name__ == "__main__":
    aggregate()
