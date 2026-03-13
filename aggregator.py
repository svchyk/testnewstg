import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re

# Настройки
CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']

def get_tg_posts(channel_name):
    posts = []
    # Используем ?embed=1 для более чистого получения медиа-данных
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=40)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            if not link_area or not text_area: continue
            
            # Логика видео
            video_tag = item.find('video')
            media_html = ""
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

def generate_static_summary(all_posts):
    now = datetime.datetime.now().strftime("%d.%m %H:%M")
    src_links = ", ".join([f'<a href="https://t.me/{ch}" target="_blank">@{ch}</a>' for ch in CHANNELS])
    
    return f"""
    <div class="summary-card">
        <div class="summary-header">
            <span>STRATEGIC INTELLIGENCE</span>
            <span>{now} MSK</span>
        </div>
        
        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">89%</span></div>
            <div class="stat-box">Наземная оп.<span class="stat-val">48%</span></div>
            <div class="stat-box">БПЛА West<span class="stat-val" style="color:#ff3b30;">182</span></div>
            <div class="stat-box">БПЛА Iran+<span class="stat-val" style="color:#ff9500;">341</span></div>
        </div>

        <div class="summary-content">
            <div class="s-section">
                <b>ОПЕРАТИВНЫЙ АНАЛИЗ</b><br>
                Подтвержден вылет B-2. Группировка CENTCOM переведена в состояние "Эпическая ярость". 
                Цель: превентивное лишение Ирана возможности восстановления потенциала.
            </div>
            
            <div class="s-section">
                <b>ОРМУЗСКИЙ ПРОЛИВ И РЫНКИ</b><br>
                Наблюдается аномальное скопление танкеров у входа в залив. Нефть Brent реагирует ростом волатильности.
            </div>

            <div class="s-section highlight">
                <b>СЛУХИ И НЕОЧЕВИДНОЕ</b><br>
                • В закрытых каналах сообщают о переброске спецподразделений в Иорданию.<br>
                • Слух: Возможна временная блокировка гражданского интернета в зонах ПВО Ирана.<br>
                • Факты: Массовый вылет стратегической авиации США с базы Диего-Гарсия.
            </div>
        </div>
        <div class="summary-footer">Источники: {src_links}</div>
    </div>
    """

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

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>Intelligence</title>
    <style>
        body {{ background: #f2f2f7; font-family: -apple-system, system-ui, sans-serif; margin: 0; color: #000; padding-bottom: 50px; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 10px; }}
        .summary-card {{ background: #fff; border-radius: 28px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid rgba(0,122,255,0.1); }}
        .summary-header {{ display: flex; justify-content: space-between; font-size: 10px; font-weight: 800; color: #8e8e93; margin-bottom: 15px; letter-spacing: 0.5px; }}
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }}
        .stat-box {{ background: #f8f9fa; padding: 12px; border-radius: 18px; }}
        .stat-val {{ display: block; font-size: 22px; font-weight: 800; color: #007aff; margin-top: 4px; }}
        .summary-content {{ font-size: 13.5px; line-height: 1.5; }}
        .s-section {{ margin-bottom: 12px; }}
        .highlight {{ background: rgba(0,122,255,0.05); padding: 12px; border-radius: 15px; border-left: 3px solid #007aff; }}
        .summary-footer {{ font-size: 10px; opacity: 0.5; margin-top: 10px; }}
        .summary-footer a {{ color: #007aff; text-decoration: none; }}
        
        .card {{ background: #fff; border-radius: 24px; padding: 16px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }}
        .media-wrap {{ margin: -16px -16px 12px -16px; }}
        .media-wrap img, .media-wrap video {{ width: 100%; border-radius: 24px 24px 0 0; display: block; }}
        .post-meta {{ font-size: 12px; font-weight: 700; color: #007aff; margin-bottom: 8px; }}
        .post-content {{ font-size: 15px; line-height: 1.4; }}
        
        .footer-btns {{ display: flex; align-items: center; gap: 20px; margin-top: 15px; padding-top: 12px; border-top: 0.5px solid #eee; }}
        .action-icon {{ font-size: 22px; cursor: pointer; color: #ccc; text-decoration: none; line-height: 1; }}
        .action-icon:hover {{ color: #007aff; }}
    </style>
</head>
<body>
    <div class="container">
        {generate_static_summary(archive)}
        <div id="feed">
            {''.join([f"""
            <div class="card">
                {p['media_html']}
                <div class="post-meta">@{p['full_name']}</div>
                <div class="post-content">{p['content']}</div>
                <div class="footer-btns">
                    <span class="action-icon">☆</span>
                    <a href="{p['link']}" class="action-icon" target="_blank">⎋</a>
                </div>
            </div>
            """ for p in archive[:50]])}
        </div>
    </div>
</body>
</html>
''')

if __name__ == "__main__":
    aggregate()
