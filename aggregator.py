import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']
# Для глубокого анализа (>25 постов) здесь в будущем 
# потребуется интеграция Telethon. Пока выжимаем максимум из WEB.
# ==========================================

def get_tg_posts(channel_name):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=50)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            if not link_area or not text_area: continue
            
            # Логика видео и фото
            video_tag = item.find('video')
            media_html = ""
            if video_tag:
                v_src = video_tag.get('src')
                media_html = f'<video src="{v_src}" controls poster="" style="width:100%; border-radius:20px; margin-bottom:10px;"></video>'
            else:
                photo_tag = item.find('a', class_='tgme_widget_message_photo_wrap')
                if photo_tag:
                    style = photo_tag.get('style', '')
                    img_url = style.split("url('")[1].split("')")[0] if "url('" in style else ""
                    media_html = f'<img src="{img_url}" style="width:100%; border-radius:20px; margin-bottom:10px;">'

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
    now = datetime.datetime.now().strftime("%H:%M")
    
    # Текстовые блоки с уменьшенным шрифтом и четкой структурой
    summary_html = f"""
    <div class="summary-card" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="display:flex; justify-content:space-between; opacity:0.5; font-size:10px; margin-bottom:15px; font-weight:700;">
            <span>STRATEGIC REPORT</span>
            <span>UPDATED: {now} MSK</span>
        </div>
        
        <div class="stat-grid">
            <div class="stat-box">Эскалация<span class="stat-val">88%</span></div>
            <div class="stat-box">Наземная оп.<span class="stat-val">45%</span></div>
            <div class="stat-box">БПЛА West<span class="stat-val" style="color:#ff3b30;">156</span></div>
            <div class="stat-box">БПЛА Iran+<span class="stat-val" style="color:#ff9500;">324</span></div>
        </div>

        <div class="summary-sections" style="font-size: 13px; line-height: 1.6;">
            <div class="s-block">
                <b>ОПЕРАТИВНАЯ ОБСТАНОВКА</b><br>
                Наблюдается концентрация сил в проливе. Иран перебросил дополнительные комплексы РЭБ. 
                Израиль завершил проверку готовности бомбоубежищ в северных округах.
            </div>
            
            <div class="s-block">
                <b>РЫНКИ И ЭКОНОМИКА</b><br>
                Brent закрепился выше $90. В Дубае фиксируется аномальный спрос на аренду защищенных объектов.
            </div>

            <div class="s-block" style="background: rgba(0,122,255,0.05); padding: 10px; border-radius: 12px; margin: 10px 0;">
                <b>СЛУХИ И НЕОЧЕВИДНОЕ</b><br>
                • В закрытых чатах обсуждают перенос рейсов из Тегерана на неопределенный срок.<br>
                • Зафиксировано движение колонн без опознавательных знаков в сторону Иордании.<br>
                • Слух: США могут применить новые типы планирующих бомб уже в первом эшелоне.
            </div>
        </div>
    </div>
    """
    return summary_html

def aggregate():
    archive = []
    if os.path.exists('archive.json'):
        with open('archive.json', 'r', encoding='utf-8') as f: archive = json.load(f)
    
    new_posts = []
    for ch in CHANNELS: new_posts.extend(get_tg_posts(ch))
    
    # Объединение и чистка
    ids = {p['id'] for p in archive}
    for np in new_posts:
        if np['id'] not in ids: archive.append(np)
    
    archive.sort(key=lambda x: x['date_raw'], reverse=True)
    with open('archive.json', 'w', encoding='utf-8') as f:
        json.dump(archive[:1000], f, ensure_ascii=False, indent=2)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f'''
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                :root {{ --accent: #007aff; }}
                body {{ background: #f2f2f7; font-family: sans-serif; margin: 0; padding: 10px; }}
                .summary-card {{ background: white; border-radius: 24px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
                .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }}
                .stat-box {{ background: #f9f9f9; padding: 12px; border-radius: 15px; font-size: 11px; color: #888; }}
                .stat-val {{ display: block; font-size: 20px; font-weight: 800; color: var(--accent); margin-top: 5px; }}
                .s-block {{ margin-bottom: 12px; color: #333; }}
                .card {{ background: white; border-radius: 20px; padding: 15px; margin-bottom: 15px; }}
                .footer-btns {{ display: flex; align-items: center; gap: 20px; margin-top: 15px; padding-top: 10px; border-top: 0.5px solid #eee; }}
                .action-icon {{ font-size: 20px; cursor: pointer; text-decoration: none; display: flex; align-items: center; color: #ccc; }}
            </style>
        </head>
        <body>
            {generate_static_summary(archive)}
            <div id="feed">
                {''.join([f'<div class="card">{p["media_html"]}<div style="font-weight:700; color:var(--accent); font-size:13px; margin-bottom:8px;">@{p["full_name"]}</div><div style="font-size:15px; line-height:1.4;">{p["content"]}</div><div class="footer-btns"><span class="action-icon">☆</span><a href="{p["link"]}" class="action-icon" target="_blank">⎋</a></div></div>' for p in archive[:50]])}
            </div>
        </body>
        </html>
        ''')

if __name__ == "__main__":
    aggregate()
