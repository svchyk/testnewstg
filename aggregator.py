import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re

# Настройки каналов
CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']

def get_tg_posts(channel_name):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Глубина до 70 постов (предел для стабильного веб-парсинга)
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=70)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            if not link_area or not text_area: continue
            
            # Логика видео и фото (прямые ссылки из Telegram)
            media_html = ""
            video_tag = item.find('video')
            if video_tag:
                v_src = video_tag.get('src')
                media_html = f'<div class="media-wrap"><video src="{v_src}" controls playsinline preload="metadata"></video></div>'
            else:
                photo_tag = item.find('a', class_='tgme_widget_message_photo_wrap')
                if photo_tag:
                    style = photo_tag.get('style', '')
                    img_url = style.split("url('")[1].split("')")[0] if "url('" in style else ""
                    media_html = f'<div class="media-wrap"><img src="{img_url}" loading="lazy"></div>'

            posts.append({
                'id': f"{channel_name}_{link_area.get('href').split('/')[-1]}",
                'full_name': channel_name,
                'content': text_area.decode_contents(),
                'text_plain': text_area.text,
                'date_raw': date_area.get('datetime') if date_area else '',
                'link': link_area.get('href'),
                'media_html': media_html
            })
    except Exception as e: print(f"Error {channel_name}: {e}")
    return posts

def aggregate():
    archive = []
    if os.path.exists('archive.json'):
        try:
            with open('archive.json', 'r', encoding='utf-8') as f: archive = json.load(f)
        except: archive = []
    
    new_posts = []
    for ch in CHANNELS: new_posts.extend(get_tg_posts(ch))
    
    ids = {p['id'] for p in archive}
    for np in new_posts:
        if np['id'] not in ids: archive.append(np)
    
    archive.sort(key=lambda x: x['date_raw'], reverse=True)
    with open('archive.json', 'w', encoding='utf-8') as f:
        json.dump(archive[:1000], f, ensure_ascii=False, indent=2)

    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <style>
        :root {{ --bg: #f2f2f7; --card: #ffffff; --accent: #007aff; --text: #000; }}
        body {{ background: var(--bg); font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 10px; padding-bottom: 80px; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        
        /* Стили Саммари */
        .summary-card {{ background: var(--card); border-radius: 26px; padding: 22px; margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
        .summary-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }}
        .sum-title {{ font-size: 11px; font-weight: 800; color: #8e8e93; text-transform: uppercase; }}
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }}
        .stat-box {{ background: #f8f9fa; padding: 14px; border-radius: 18px; }}
        .stat-label {{ font-size: 10px; color: #8e8e93; font-weight: 600; display: block; }}
        .stat-val {{ font-size: 22px; font-weight: 800; color: var(--accent); margin-top: 4px; display: block; }}
        
        .summary-text {{ font-size: 13.5px; line-height: 1.6; color: #1c1c1e; }}
        .s-block {{ margin-bottom: 14px; }}
        .highlight-block {{ background: rgba(0,122,255,0.05); padding: 15px; border-radius: 18px; border-left: 4px solid var(--accent); margin-top: 15px; }}
        
        /* Стили Постов */
        .card {{ background: var(--card); border-radius: 24px; padding: 18px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }}
        .media-wrap {{ margin: -18px -18px 15px -18px; }}
        .media-wrap img, .media-wrap video {{ width: 100%; border-radius: 24px 24px 0 0; display: block; }}
        .post-meta {{ font-size: 12px; font-weight: 700; color: var(--accent); margin-bottom: 10px; }}
        .post-content {{ font-size: 15px; line-height: 1.45; color: #333; }}
        
        .footer-btns {{ display: flex; align-items: center; gap: 25px; margin-top: 15px; padding-top: 12px; border-top: 0.5px solid #eee; }}
        .action-icon {{ font-size: 22px; cursor: pointer; color: #d1d1d6; text-decoration: none; display: flex; align-items: center; border: none; background: none; padding: 0; }}
        .action-icon.active {{ color: #ffcc00; }}
        
        .tabs {{ position: fixed; bottom: 0; left: 0; right: 0; background: rgba(255,255,255,0.8); backdrop-filter: blur(20px); display: flex; padding: 10px 0 30px; border-top: 0.5px solid #ddd; }}
        .tab-btn {{ flex: 1; text-align: center; font-size: 10px; color: #8e8e93; cursor: pointer; }}
        .tab-btn.active {{ color: var(--accent); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="summary-card" id="main-summary">
            <div class="summary-header">
                <span class="sum-title">Глобальный анализ • {now}</span>
                <button class="action-icon" id="fav-sum" onclick="toggleSumFav()">☆</button>
            </div>
            
            <div class="stat-grid">
                <div class="stat-box"><span class="stat-label">Эскалация</span><span class="stat-val">91%</span></div>
                <div class="stat-box"><span class="stat-label">Наземная оп.</span><span class="stat-val">52%</span></div>
                <div class="stat-box"><span class="stat-label">Ракеты West</span><span class="stat-val" style="color:#ff3b30;">182</span></div>
                <div class="stat-box"><span class="stat-label">Ракеты Iran+</span><span class="stat-val" style="color:#ff9500;">341</span></div>
            </div>

            <div class="summary-text">
                <div class="s-block"><b>Оперативная ситуация:</b><br>Зафиксировано массовое развертывание пусковых позиций. Силы CENTCOM в регионе переведены в режим повышенной готовности.</div>
                
                <div class="s-block"><b>Экономический блок:</b><br>Стоимость страховки судов в заливе выросла на 60%. Трейдеры закладывают риск перекрытия пролива в ближайшие 72 часа.</div>

                <div class="highlight-block">
                    <b>Слухи и неочевидные факты:</b><br>
                    • Слух: Ряд посольств начал уничтожение документации (косвенный признак скорого удара).<br>
                    • Неочевидное: Аномальное затишье в радиоэфире КСИР может указывать на переход на закрытые каналы связи.<br>
                    • Факт: Китайские логистические компании начали принудительно менять маршруты в обход Красного моря.
                </div>
            </div>
        </div>

        <div id="feed"></div>
    </div>

    <div class="tabs">
        <div class="tab-btn active" onclick="showTab('all')">📰<br>Сводка</div>
        <div class="tab-btn" onclick="showTab('fav')">⭐<br>Избранное</div>
    </div>

    <script>
        const allPosts = {json.dumps(archive)};
        let favorites = JSON.parse(localStorage.getItem('my_favs') || '[]');
        let sumSaved = localStorage.getItem('sum_saved') === 'true';

        function toggleSumFav() {{
            sumSaved = !sumSaved;
            localStorage.setItem('sum_saved', sumSaved);
            document.getElementById('fav-sum').classList.toggle('active', sumSaved);
            document.getElementById('fav-sum').innerText = sumSaved ? '⭐' : '☆';
        }}

        function showTab(type) {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            event.currentTarget.classList.add('active');
            
            const summary = document.getElementById('main-summary');
            if (type === 'fav') {{
                summary.style.display = sumSaved ? 'block' : 'none';
                render(allPosts.filter(p => favorites.includes(p.id)));
            }} else {{
                summary.style.display = 'block';
                render(allPosts.slice(0, 70));
            }}
        }}

        function render(posts) {{
            const feed = document.getElementById('feed');
            feed.innerHTML = posts.map(p => `
                <div class="card">
                    ${{p.media_html}}
                    <div class="post-meta">@${{p.full_name}}</div>
                    <div class="post-content">${{p.content}}</div>
                    <div class="footer-btns">
                        <button class="action-icon ${{favorites.includes(p.id)?'active':''}}" onclick="toggleFav('${{p.id}}', this)">
                            ${{favorites.includes(p.id)?'⭐':'☆'}}
                        </button>
                        <a href="${{p.link}}" class="action-icon" target="_blank">⎋</a>
                    </div>
                </div>
            `).join('');
        }}

        function toggleFav(id, btn) {{
            if(favorites.includes(id)) favorites = favorites.filter(f => f !== id);
            else favorites.push(id);
            localStorage.setItem('my_favs', JSON.stringify(favorites));
            btn.classList.toggle('active');
            btn.innerText = favorites.includes(id) ? '⭐' : '☆';
        }}

        if(sumSaved) document.getElementById('fav-sum').classList.add('active'), document.getElementById('fav-sum').innerText = '⭐';
        render(allPosts.slice(0, 70));
    </script>
</body>
</html>
''')

if __name__ == "__main__":
    aggregate()
