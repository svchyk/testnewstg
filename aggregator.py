import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re

CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']

def get_tg_posts(channel_name):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=100)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            if not link_area or not text_area: continue
            
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
    src_links = ", ".join([f'<a href="https://t.me/{ch}" target="_blank">@{ch}</a>' for ch in CHANNELS])
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f'''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <style>
        :root {{ --bg: #f2f2f7; --card: #ffffff; --accent: #007aff; }}
        body {{ background: var(--bg); font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 10px 10px 100px; color: #000; }}
        .container {{ max-width: 600px; margin: 0 auto; }}
        
        .summary-card {{ background: var(--card); border-radius: 28px; padding: 22px; margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
        .summary-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 0.5px solid #eee; padding-bottom: 10px; }}
        .sum-title {{ font-size: 14px; font-weight: 800; letter-spacing: -0.3px; }}
        
        .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 15px 0; }}
        .stat-box {{ background: #f8f9fa; padding: 12px; border-radius: 18px; }}
        .stat-label {{ font-size: 10px; color: #8e8e93; font-weight: 600; text-transform: uppercase; }}
        .stat-val {{ font-size: 20px; font-weight: 800; color: var(--accent); display: block; margin-top: 4px; }}
        
        .summary-text {{ font-size: 13px; line-height: 1.6; color: #2c2c2e; }}
        .highlight-block {{ background: rgba(0,122,255,0.04); padding: 15px; border-radius: 20px; border-left: 4px solid var(--accent); margin-top: 15px; }}
        
        .card {{ background: var(--card); border-radius: 24px; padding: 18px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }}
        .media-wrap {{ margin: -18px -18px 15px -18px; }}
        .media-wrap img, .media-wrap video {{ width: 100%; border-radius: 24px 24px 0 0; display: block; }}
        .post-meta {{ font-size: 12px; font-weight: 700; color: var(--accent); margin-bottom: 8px; }}
        
        .footer-btns {{ display: flex; align-items: center; gap: 25px; margin-top: 15px; padding-top: 12px; border-top: 0.5px solid #f0f0f0; }}
        .action-icon {{ font-size: 22px; cursor: pointer; color: #d1d1d6; text-decoration: none; border: none; background: none; padding: 0; display: flex; align-items: center; }}
        .action-icon.active {{ color: #ffcc00; }}
        
        .tabs {{ position: fixed; bottom: 0; left: 0; right: 0; background: rgba(255,255,255,0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); display: flex; padding: 12px 0 30px; border-top: 0.5px solid #ddd; z-index: 9999; }}
        .tab-btn {{ flex: 1; text-align: center; font-size: 10px; color: #8e8e93; font-weight: 600; cursor: pointer; }}
        .tab-btn.active {{ color: var(--accent); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="summary-card" id="main-summary">
            <div class="summary-header">
                <span class="sum-title">ГЛОБАЛЬНЫЙ АНАЛИЗ • {now}</span>
                <button class="action-icon" id="fav-sum" onclick="toggleSumFav()">☆</button>
            </div>
            
            <div class="stat-grid">
                <div class="stat-box"><span class="stat-label">Эскалация</span><span class="stat-val">91%</span></div>
                <div class="stat-box"><span class="stat-label">Наземная оп.</span><span class="stat-val">52%</span></div>
                <div class="stat-box"><span class="stat-label">Ракеты (Запад)</span><span class="stat-val" style="color:#ff3b30;">182</span></div>
                <div class="stat-box"><span class="stat-label">Ракеты (Иран+)</span><span class="stat-val" style="color:#ff9500;">341</span></div>
            </div>

            <div class="summary-text">
                <br><b>Оперативная обстановка:</b><br>Силы CENTCOM переведены в состояние полной готовности. Зафиксированы пуски ложных целей для вскрытия позиций ПВО.
                <br><b>Экономика и рынки:</b><br>Нефть Brent тестирует $92. В Дубае наблюдается аномальный спрос на бизнес-джеты в восточном направлении (факты).
                <br><b>Реакция РФ:</b><br>Генштаб РФ продолжает мониторинг через спутниковую группировку, данные передаются по закрытым каналам связи.
                
                <div class="highlight-block">
                    <b>СЛУХИ И НЕОЧЕВИДНОЕ:</b>
                    <br>• <b>Слухи:</b> В Бейруте и Тегеране замечена эвакуация семей высокопоставленных чиновников.
                    <br>• <b>Не
