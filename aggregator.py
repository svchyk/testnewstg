import requests
from bs4 import BeautifulSoup
import datetime
import json
import os

CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']
ARCHIVE_FILE = 'archive.json'

def get_tg_posts(channel_name):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        channel_title_tag = soup.find('div', class_='tgme_channel_info_header_title')
        full_name = channel_title_tag.text.strip() if channel_title_tag else channel_name

        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=20)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            msg_id = link_area.get('href').split('/')[-1] if link_area else ""
            
            photo = item.find('a', class_='tgme_widget_message_photo_wrap')
            video = item.find('i', class_='tgme_widget_message_video_thumb')
            media_url = ""
            style = (photo or video).get('style', '') if (photo or video) else ""
            if "url('" in style:
                media_url = style.split("url('")[1].split("')")[0]

            if text_area:
                posts.append({
                    'id': f"{channel_name}_{msg_id}",
                    'full_name': full_name,
                    'content': text_area.decode_contents(),
                    'date_raw': date_area.get('datetime') if date_area else '',
                    'link': link_area.get('href') if link_area else f"https://t.me/{channel_name}",
                    'handle': channel_name,
                    'media': media_url
                })
    except Exception as e: print(f"Error {channel_name}: {e}")
    return posts

def aggregate():
    # 1. Загружаем старый архив
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            archive = json.load(f)
    else:
        archive = []

    # 2. Собираем новые посты
    new_posts = []
    for ch in CHANNELS:
        new_posts.extend(get_tg_posts(ch))

    # 3. Объединяем, убирая дубликаты по ID
    existing_ids = {p['id'] for p in archive}
    for np in new_posts:
        if np['id'] not in existing_ids:
            archive.append(np)

    # Сортировка всего архива (свежие сверху)
    archive.sort(key=lambda x: x['date_raw'], reverse=True)
    
    # Сохраняем обновленный архив (ограничим 500 записями для экономии места)
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive[:500], f, ensure_ascii=False, indent=2)

    # 4. Генерируем современный интерфейс
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>iOS 26 News</title>
    <style>
        :root {
            --bg: #f2f2f7; --card: rgba(255,255,255,0.8); --text: #000; --accent: #007aff; --blur: blur(20px);
        }
        [data-theme="dark"] {
            --bg: #000; --card: rgba(28,28,30,0.8); --text: #fff; --accent: #0a84ff;
        }
        [data-theme="sepia"] {
            --bg: #f4ecd8; --card: rgba(250,242,225,0.9); --text: #5b4636; --accent: #a0522d;
        }
        
        body { background: var(--bg); color: var(--text); font-family: -apple-system, system-ui; margin: 0; transition: 0.3s; }
        
        /* iOS Blur Header */
        header { 
            position: sticky; top: 0; z-index: 100; background: var(--card); 
            backdrop-filter: var(--blur); padding: 20px; border-bottom: 0.5px solid rgba(0,0,0,0.1);
        }
        
        .nav-scroller { display: flex; gap: 15px; overflow-x: auto; padding: 10px 0; scrollbar-width: none; }
        .theme-btn { 
            padding: 8px 16px; border-radius: 20px; border: none; cursor: pointer;
            background: rgba(120,120,128,0.16); color: var(--text); font-weight: 500;
        }

        .container { max-width: 600px; margin: 0 auto; padding: 15px; }
        
        .card { 
            background: var(--card); backdrop-filter: var(--blur); 
            border-radius: 20px; padding: 18px; margin-bottom: 20px; 
            box-shadow: 0 4px 30px rgba(0,0,0,0.05); border: 0.5px solid rgba(255,255,255,0.1);
        }
        
        .card-header { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 0.9em; }
        .channel-name { color: var(--accent); font-weight: 600; text-decoration: none; }
        
        .media-img { width: 100%; border-radius: 12px; margin-bottom: 12px; display: block; }
        .content { line-height: 1.5; font-size: 17px; }
        
        .actions { margin-top: 15px; display: flex; gap: 20px; }
        .fav-btn { background: none; border: none; font-size: 1.2em; cursor: pointer; filter: grayscale(1); }
        .fav-btn.active { filter: grayscale(0); }

        /* Tabs */
        .tabs { display: flex; justify-content: space-around; background: var(--card); backdrop-filter: var(--blur); position: fixed; bottom: 0; width: 100%; padding: 10px 0; border-top: 0.5px solid rgba(0,0,0,0.1); }
        .tab { text-align: center; font-size: 10px; color: #8e8e93; text-decoration: none; flex: 1; }
        .tab.active { color: var(--accent); }
    </style>
</head>
<body>

<header>
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2 style="margin:0;">News</h2>
        <div style="display:flex; gap:5px;">
            <button class="theme-btn" onclick="setTheme('light')">☀️</button>
            <button class="theme-btn" onclick="setTheme('dark')">🌙</button>
            <button class="theme-btn" onclick="setTheme('sepia')">📜</button>
        </div>
    </div>
</header>

<div class="container" id="feed">
    </div>

<div class="tabs">
    <a href="#" class="tab active" onclick="showSection('all')">📰<br>Лента</a>
    <a href="#" class="tab" onclick="showSection('fav')">⭐<br>Избранное</a>
    <a href="#" class="tab" onclick="showSection('archive')">📦<br>Архив</a>
</div>

<script>
    const allPosts = ''' + json.dumps(archive) + ''';
    let favorites = JSON.parse(localStorage.getItem('favs') || '[]');

    function setTheme(t) {
        document.documentElement.setAttribute('data-theme', t);
        localStorage.setItem('theme', t);
    }

    function toggleFav(id) {
        if(favorites.includes(id)) favorites = favorites.filter(f => f !== id);
        else favorites.push(id);
        localStorage.setItem('favs', JSON.stringify(favorites));
        render();
    }

    function render(filter = 'all') {
        const container = document.getElementById('feed');
        let html = '';
        let displayPosts = allPosts;
        
        if(filter === 'all') displayPosts = allPosts.slice(0, 50);
        if(filter === 'fav') displayPosts = allPosts.filter(p => favorites.includes(p.id));
        if(filter === 'archive') displayPosts = allPosts.slice(50);

        displayPosts.forEach(p => {
            const isFav = favorites.includes(p.id);
            html += `
                <div class="card">
                    <div class="card-header">
                        <a href="https://t.me/${p.handle}" class="channel-name" target="_blank">@${p.full_name}</a>
                        <span style="opacity:0.6">${p.date_raw.slice(11,16)}</span>
                    </div>
                    ${p.media ? `<img src="${p.media}" class="media-img">` : ''}
                    <div class="content">${p.content}</div>
                    <div class="actions">
                        <button class="fav-btn ${isFav?'active':''}" onclick="toggleFav('${p.id}')">⭐</button>
                        <a href="${p.link}" target="_blank" style="text-decoration:none; font-size:0.9em;">↗️</a>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html || '<p style="text-align:center; margin-top:50px;">Тут пока ничего нет</p>';
    }

    function showSection(s) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        event.currentTarget.classList.add('active');
        render(s);
    }

    // Init
    setTheme(localStorage.getItem('theme') || 'light');
    render();
</script>
</body>
</html>''')

if __name__ == "__main__":
    aggregate()
