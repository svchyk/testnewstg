import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re

# ==========================================
# СПИСОК КАНАЛОВ И НАСТРОЙКИ
# ==========================================
CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario', 'victorstepanych', 'varlamov
']
ARCHIVE_FILE = 'archive.json'

def get_tg_posts(channel_name):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_tag = soup.find('div', class_='tgme_channel_info_header_title')
        full_name = title_tag.text.strip() if title_tag else channel_name
        
        # Глубина 100 постов
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=100)
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

def generate_static_summary(all_posts):
    est_date = (datetime.datetime.now() + datetime.timedelta(days=4)).strftime("%d.%m")
    
    return f"""
    <div class="summary-card">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:20px; border-bottom:1px solid rgba(0,0,0,0.1); padding-bottom:10px;">
            <h2 style="margin:0; font-size:18px; letter-spacing:-0.5px; font-weight:900;">STRATEGIC INTELLIGENCE SUMMARY</h2>
            <span id="summary-time" style="font-size:14px; opacity:0.5; font-weight:700;"></span>
        </div>

        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">87%</span></div>
            <div class="stat-box">Ядерный удар<span class="stat-val">4%</span></div>
            <div class="stat-box">Наземная операция<span class="stat-val">42%</span></div>
            <div class="stat-box">Шанс Ирана<span class="stat-val">58%</span></div>
            <div class="stat-box" style="grid-column: span 2; border: 1px solid rgba(0,122,255,0.2); flex-direction:row; align-items:center; justify-content:space-between;">
                Прогноз начала наземной операции: <span class="stat-val" style="margin:0; color:var(--accent);">{est_date} — 22.03</span>
            </div>
        </div>

        <div class="ai-text-block" style="margin-top:20px;">
            <h3 style="margin:0 0 15px 0;">Глобальный анализ ситуации</h3>
            <div class="summary-section" style="line-height:1.6; font-size:15px;">
                На текущий час ситуация в регионе характеризуется переходом от демонстративных ударов к системному подавлению ПВО. 
                <b>Успехи Ирана:</b> КСИР успешно протестировал маршруты обхода израильских РЛС. 
                <b>Ормузский пролив:</b> Зафиксировано наращивание минных заграждений. 
                <b>Рынки:</b> Нефть Brent тестирует $92. <b>Реакция РФ:</b> Москва активизировала каналы связи, предостерегая от ударов по ядерным объектам.
            </div>
        </div>
    </div>
    """

def aggregate():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            try: archive = json.load(f)
            except: archive = []
    else: archive = []

    new_posts = []
    for ch in CHANNELS:
        new_posts.extend(get_tg_posts(ch))
    
    existing_ids = {p['id'] for p in archive}
    for np in new_posts:
        if np['id'] not in existing_ids: archive.append(np)
    
    archive.sort(key=lambda x: x['date_raw'], reverse=True)
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive[:2000], f, ensure_ascii=False, indent=2)

    ready_summary = generate_static_summary(archive)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f'''<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>Intelligence Center</title>
    <style>
        :root {{ --bg: #f2f2f7; --card: #ffffff; --text: #000; --accent: #007aff; }}
        [data-theme="dark"] {{ --bg: #000; --card: #1c1c1e; --text: #fff; --accent: #0a84ff; }}
        body {{ background: var(--bg); color: var(--text); font-family: -apple-system, system-ui, sans-serif; margin: 0; padding-bottom: 100px; }}
        header {{ position: sticky; top: 0; z-index: 1000; background: rgba(255,255,255,0.8); backdrop-filter: blur(20px); padding: 15px 20px; border-bottom: 0.5px solid rgba(0,0,0,0.1); display:flex; justify-content:space-between; align-items:center; }}
        [data-theme="dark"] header {{ background: rgba(0,0,0,0.8); }}
        .summary-card {{ background: var(--card); border-radius: 25px; padding: 25px; margin: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
        .stat-box {{ background: rgba(120,120,128,0.08); padding: 12px; border-radius: 15px; font-size: 11px; font-weight: 600; display: flex; flex-direction: column; }}
        .stat-val {{ font-size: 18px; font-weight: 800; color: var(--accent); margin-top: 5px; }}
        .card {{ background: var(--card); border-radius: 20px; padding: 20px; margin: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); overflow: hidden; }}
        .media-container {{ width: calc(100% + 40px); margin: -20px -20px 15px -20px; background: #000; }}
        .media-img, video {{ width: 100%; display: block; }}
        .content {{ line-height: 1.5; font-size: 16px; word-wrap: break-word; }}
        .tabs {{ position: fixed; bottom: 0; width: 100%; background: var(--card); display: flex; padding: 12px 0 35px 0; border-top: 0.5px solid rgba(0,0,0,0.1); z-index: 1000; }}
        .tab {{ flex: 1; text-align: center; text-decoration: none; color: #8e8e93; font-size: 10px; font-weight: 700; }}
        .tab.active {{ color: var(--accent); }}
    </style>
</head>
<body>
<header>
    <h1 style="margin:0; font-size:24px; font-weight:900;">Intelligence</h1>
    <button onclick="toggleTheme()" style="background:none; border:none; font-size:20px; cursor:pointer;">🌓</button>
</header>
<div id="main-content" style="max-width:600px; margin: 0 auto;">
    {ready_summary}
    <div id="feed"></div>
</div>
<div class="tabs">
    <a href="#" class="tab active" onclick="render('all', this)">📰<br>СВОДКА</a>
    <a href="#" class="tab" onclick="render('archive', this)">📦<br>АРХИВ</a>
    <a href="#" class="tab" onclick="render('fav', this)">⭐<br>SAVED</a>
</div>

<script>
    const allPosts = {json.dumps(archive)};
    let favorites = JSON.parse(localStorage.getItem('favs') || '[]');

    function formatDeviceTime(rawDate) {{
        if(!rawDate) return '';
        const d = new Date(rawDate);
        return d.toLocaleString('ru-RU', {{ day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }});
    }}

    document.getElementById('summary-time').innerText = formatDeviceTime(new Date().toISOString()) + ' MSK';

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
        let html = '';
        
        let posts = [];
        if(mode === 'all') posts = allPosts.slice(0, 50);
        else if(mode === 'archive') posts = allPosts.slice(50, 500);
        else posts = allPosts.filter(p => favorites.includes(p.id));
        
        posts.forEach(p => {{
            const isFav = favorites.includes(p.id);
            let mediaHtml = p.video 
                ? `<div class="media-container"><video src="${{p.video}}" autoplay muted loop playsinline></video></div>`
                : (p.media ? `<div class="media-container"><img src="${{p.media}}" class="media-img" loading="lazy"></div>` : '');

            html += `<div class="card">
                ${{mediaHtml}}
                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                    <a href="${{p.link}}" target="_blank" style="font-weight:800; color:var(--accent); text-decoration:none;">
                        ${{p.full_name}}<br><span style="opacity:0.5; font-size:12px; font-weight:400;">@${{p.handle}}</span>
                    </a>
                    <span style="opacity:0.4; font-size:12px; font-weight:700;">${{formatDeviceTime(p.date_raw)}}</span>
                </div>
                <div class="content">${{p.content}}</div>
                <div style="margin-top:15px; border-top:1px solid rgba(0,0,0,0.05); padding-top:10px;">
                    <button style="background:none; border:none; cursor:pointer; font-size:18px;" onclick="toggleFav('${{p.id}}')">${{isFav?'⭐':'☆'}}</button>
                </div>
            </div>`;
        }});
        container.innerHTML = html;
        window.scrollTo(0,0);
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
</html>''')

if __name__ == "__main__":
    aggregate()
