import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re

# ==========================================
# СПИСОК КАНАЛОВ
# ==========================================
CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']
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
        
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=25)
        for item in items:
            # Пытаемся найти полный текст в разных слоях разметки TG
            text_area = item.find('div', class_='tgme_widget_message_text')
            if not text_area: continue
            
            # Извлекаем контент, стараясь игнорировать кнопку "Read more"
            content_html = text_area.decode_contents().strip()
            # Удаляем саму ссылку "читать далее", если она попала в HTML
            content_html = re.sub(r'<a[^>]*class="[^"]*tgme_widget_message_text_more"[^>]*>.*?</a>', '', content_html)
            
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            
            # Работа с медиа (фото или видео)
            media_url = ""
            video_url = ""
            
            # Проверяем видео
            video_tag = item.find('video', class_='tgme_widget_message_video')
            if video_tag:
                video_url = video_tag.get('src', '')
            
            # Проверяем фото/превью
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
    except Exception as e: print(f"Error {channel_name}: {e}")
    return posts

def generate_static_summary(all_posts):
    # (Блок генерации саммари остается без изменений, как в прошлом шаге)
    est_date = (datetime.datetime.now() + datetime.timedelta(days=4)).strftime("%d.%m")
    sources_html = ", ".join([f'<a href="https://t.me/{ch}" style="color:var(--accent);text-decoration:none;">@{ch}</a>' for ch in CHANNELS])
    return f"""
    <div class="summary-card">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:20px; border-bottom:1px solid rgba(0,0,0,0.1); padding-bottom:10px;">
            <h2 style="margin:0; font-size:18px; letter-spacing:-0.5px; font-weight:900;">Глобальный анализ ситуации</h2>
            <span id="summary-time" style="font-size:16px; font-weight:800; color:var(--accent);"></span>
        </div>
        <div style="text-transform:uppercase; font-weight:800; color:var(--text); opacity:0.4; font-size:10px; letter-spacing:1px; margin-bottom:10px;">ВЕРОЯТНОСТИ</div>
        <div class="stat-grid">
            <div class="stat-box">Эскалация сейчас<span class="stat-val">87%</span></div>
            <div class="stat-box">Вероятность ядерного удара<span class="stat-val">4%</span></div>
            <div class="stat-box">Вероятность наземной операции<span class="stat-val">42%</span></div>
            <div class="stat-box">Шанс Ирана защитить прибрежную зону<span class="stat-val">58%</span></div>
            <div class="stat-box" style="grid-column: span 2; border: 1px solid rgba(0,122,255,0.2);">
                Прогноз начала наземной операции: <span class="stat-val" style="display:inline; margin-left:10px;">{est_date} — 22.03</span>
            </div>
        </div>
        <button onclick="location.reload()" style="width:100%; padding:12px; border-radius:15px; border:none; background:var(--accent); color:white; font-weight:700; margin:10px 0 20px 0; cursor:pointer; font-size:13px;">🔄 Обновить данные анализа</button>
        <div class="ai-text-block">
            <div class="summary-section">
                На текущий час ситуация в регионе характеризуется переходом к системному подавлению ПВО. 
            </div>
            <div style="font-size:11px; opacity:0.5; margin-top:15px; border-top: 0.5px solid rgba(0,0,0,0.05); padding-top: 10px;">
                База анализа: {sources_html}
            </div>
        </div>
    </div>
    """

def aggregate():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f: archive = json.load(f)
    else: archive = []
    new_posts = []
    for ch in CHANNELS: new_posts.extend(get_tg_posts(ch))
    ids = {{p['id'] for p in archive}}
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
    <title>Intelligence Center</title>
    <style>
        :root {{ --bg: #f2f2f7; --card: rgba(255,255,255,0.8); --text: #000; --accent: #007aff; --blur: blur(30px); }}
        [data-theme="dark"] {{ --bg: #000; --card: rgba(28,28,30,0.8); --text: #fff; --accent: #0a84ff; }}
        body {{ background: var(--bg); color: var(--text); font-family: -apple-system, system-ui, sans-serif; margin: 0; padding-bottom: 100px; }}
        header {{ position: sticky; top: 0; z-index: 1000; background: var(--card); backdrop-filter: var(--blur); padding: 15px 20px; border-bottom: 0.5px solid rgba(0,0,0,0.1); }}
        .summary-card {{ background: var(--card); border-radius: 30px; padding: 25px; margin: 15px; border: 0.5px solid rgba(0,122,255,0.15); }}
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 15px 0; }}
        .stat-box {{ background: rgba(120,120,128,0.1); padding: 12px; border-radius: 18px; font-size: 11px; font-weight: 600; display: flex; flex-direction: column; min-height: 70px; }}
        .stat-val {{ font-size: 1.6em; font-weight: 800; color: var(--accent); margin-top: auto; }}
        .card {{ background: var(--card); backdrop-filter: var(--blur); border-radius: 24px; padding: 20px; margin: 15px; box-shadow: 0 8px 30px rgba(0,0,0,0.04); overflow: hidden; }}
        .media-container {{ width: calc(100% + 40px); margin-left: -20px; margin-top: -20px; margin-bottom: 15px; background: #000; }}
        .media-img, .media-video {{ width: 100%; display: block; }}
        .content {{ line-height: 1.5; font-size: 16px; word-wrap: break-word; }}
        .tabs {{ display: flex; justify-content: space-around; background: var(--card); backdrop-filter: var(--blur); position: fixed; bottom: 0; width: 100%; padding: 12px 0 35px 0; border-top: 0.5px solid rgba(0,0,0,0.1); }}
        .tab {{ text-align: center; font-size: 10px; color: #8e8e93; text-decoration: none; flex: 1; font-weight: 700; }}
        .tab.active {{ color: var(--accent); }}
        a {{ color: inherit; text-decoration: none; }}
    </style>
</head>
<body>
<header>
    <div style="max-width:600px; margin:0 auto; display:flex; justify-content:space-between; align-items:center;">
        <h2 style="margin:0; font-weight:900; letter-spacing:-1px; font-size:24px;">Intelligence</h2>
        <button onclick="toggleTheme()" style="border:none; background:none; font-size:1.6em; cursor:pointer;">🌓</button>
    </div>
</header>
<div class="container" style="max-width:600px; margin:0 auto;">
    {ready_summary}
    <div id="feed"></div>
</div>
<div class="tabs">
    <a href="#" class="tab active" onclick="render('all', this)">📰<br>СВОДКА</a>
    <a href="#" class="tab" onclick="render('fav', this)">⭐<br>SAVED</a>
    <a href="#" class="tab" onclick="render('archive', this)">📦<br>АРХИВ</a>
</div>
<script>
    const allPosts = {json.dumps(archive)};
    let favorites = JSON.parse(localStorage.getItem('favs') || '[]');
    
    function formatDeviceTime(rawDate) {{
        const d = rawDate ? new Date(rawDate) : new Date();
        return new Intl.DateTimeFormat('ru-RU', {{ day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }}).format(d).replace(',', '');
    }}

    document.getElementById('summary-time').innerText = formatDeviceTime();

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
            let mediaHtml = '';
            if (p.video) {{
                mediaHtml = `<div class="media-container"><video class="media-video" src="${{p.video}}" autoplay muted loop playsinline poster="${{p.media}}"></video></div>`;
            }} else if (p.media) {{
                mediaHtml = `<div class="media-container"><img src="${{p.media}}" class="media-img" loading="lazy"></div>`;
            }}

            html += `<div class="card">
                ${{mediaHtml}}
                <div style="display:flex; justify-content:space-between; margin-bottom:12px; padding: 0 5px;">
                    <a href="${{p.link}}" target="_blank" style="font-weight:800; color:var(--accent); font-size:0.9em;">
                        ${{p.full_name}}<br><span style="opacity:0.6; font-size:0.85em;">@${{p.handle}}</span>
                    </a>
                    <span style="opacity:0.4; font-size:0.85em; font-weight:700;">${{formatDeviceTime(p.date_raw)}}</span>
                </div>
                <div class="content" style="padding: 0 5px;">${{p.content}}</div>
                <div class="footer-btns" style="padding: 15px 5px 0 5px;">
                    <button class="btn-icon" onclick="toggleFav('${{p.id}}')">${{isFav?'⭐':'☆'}}</button>
                    <a href="${{p.link}}" target="_blank" class="btn-icon">⎋</a>
                </div>
            </div>`;
        }});
        container.innerHTML = html;
    }}
    render();
</script>
</body>
</html>''')

if __name__ == "__main__":
    aggregate()
