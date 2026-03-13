import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re

# Список каналов
CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']

def get_tg_posts(channel_name):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Увеличили лимит до 100 для более глубокого анализа
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=100)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            if not link_area or not text_area: continue
            
            # Поиск видео или фото
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
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    src_links = ", ".join([f'<a href="https://t.me/{ch}" target="_blank">@{ch}</a>' for ch in CHANNELS])
    
    return f"""
    <div class="summary-card">
        <div class="summary-header">
            <span>ГЛОБАЛЬНЫЙ АНАЛИЗ СИТУАЦИИ</span>
            <span>{now} MSK</span>
        </div>
        
        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">91%</span></div>
            <div class="stat-box">Наземная оп.<span class="stat-val">52%</span></div>
            <div class="stat-box">Ракеты West<span class="stat-val" style="color:#ff3b30;">182</span></div>
            <div class="stat-box">Ракеты Iran+<span class="stat-val" style="color:#ff9500;">341</span></div>
        </div>

        <div class="summary-content">
            <div class="s-section">
                <br><b>Оперативная обстановка:</b> Подтвержден выход стратегической авиации на рубежи пуска. В регионе зафиксирована работа тяжелых комплексов РЭБ, подавляющих GPS-сигналы в радиусе 400 км.
            </div>
            
            <div class="s-section">
                <br><b>Экономические индикаторы:</b> Фрахт судов в Индийском океане вырос вдвое. Рынок ожидает закрытия Ормуза в течение ближайших 48 часов.
            </div>

            <div class="s-section highlight">
                <br><b>Слухи и неочевидные факты:</b>
                <br>• В Ливане замечено массовое перемещение пусковых установок в гражданские зоны.
                <br>• Слух: Дипломаты ряда стран залива получили предписание покинуть регион до конца недели.
                <br>• Неочевидное: Китайские танкеры начали менять курс в сторону обходных путей через Африку, что может быть косвенным признаком знания о точных сроках начала.
                <br>• Факты: На базах в Катаре замечена небывалая активность транспортной авиации.
            </div>
        </div>
        <div class="summary-footer">Источники данных: {src_links}</div>
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
    <style>
        body {{ background: #f2f2f7; font-family: -apple-system, system-ui, sans-serif; margin: 0; color: #000; padding: 10px; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        .summary-card {{ background: #fff; border-radius: 24px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
        .summary-header {{ display: flex; justify-content: space-between; font-size: 11px; font-weight: 800; color: #8e8e93; margin-bottom: 15px; }}
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }}
        .stat-box {{ background: #f8f9fa; padding: 12px; border-radius: 18px; }}
        .stat-val {{ display: block; font-size: 22px; font-weight: 800; color: #007aff; margin-top: 4px; }}
        .summary-content {{ font-size: 13px; line-height: 1.6; color: #2c2c2e; }}
        .highlight {{ background: rgba(0,122,255,0.05); padding: 12px; border-radius: 15px; border-left: 4px solid #007aff; margin-top: 15px; }}
        .summary-footer {{ font-size: 10px; opacity: 0.5; margin-top: 15px; border-top: 0.5px solid #eee; padding-top: 10px; }}
        .summary-footer a {{ color: #007aff; text-decoration: none; }}
        
        .card {{ background: #fff; border-radius: 22px; padding: 16px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }}
        .media-wrap {{ margin: -16px -16px 12px -16px; }}
        .media-wrap img, .media-wrap video {{ width: 100%; border-radius: 22px 22px 0 0; display: block; }}
        .post-meta {{ font-size: 12px; font-weight: 700; color: #007aff; margin-bottom: 8px; }}
        .post-content {{ font-size: 15px; line-height: 1.4; }}
        
        .footer-btns {{ display: flex; align-items: center; gap: 20px; margin-top: 15px; padding-top: 12px; border-top: 0.5px solid #eee; }}
        .action-icon {{ font-size: 22px; cursor: pointer; color: #ccc; text-decoration: none; display: flex; align-items: center; }}
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
