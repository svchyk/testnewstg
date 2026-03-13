import requests
from bs4 import BeautifulSoup
import datetime
import json
import os

# Список каналов
CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']
ARCHIVE_FILE = 'archive.json'

def get_tg_posts(channel_name):
    posts = []
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Получаем красивое название канала
        channel_title_tag = soup.find('div', class_='tgme_channel_info_header_title')
        full_name = channel_title_tag.text.strip() if channel_title_tag else channel_name

        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=20)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            
            if not link_area: continue
            msg_id = link_area.get('href').split('/')[-1]
            
            # Поиск медиа
            media_url = ""
            photo = item.find('a', class_='tgme_widget_message_photo_wrap')
            video = item.find('i', class_='tgme_widget_message_video_thumb')
            style = (photo or video).get('style', '') if (photo or video) else ""
            if "url('" in style:
                media_url = style.split("url('")[1].split("')")[0]

            if text_area:
                posts.append({
                    'id': f"{channel_name}_{msg_id}",
                    'full_name': full_name,
                    'content': text_area.decode_contents(),
                    'date_raw': date_area.get('datetime') if date_area else '',
                    'link': link_area.get('href'),
                    'handle': channel_name,
                    'media': media_url
                })
    except Exception as e:
        print(f"Error {channel_name}: {e}")
    return posts

def aggregate():
    # Загрузка архива
    archive = []
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                archive = json.load(f)
        except: archive = []

    # Сбор новых
    new_found = []
    for ch in CHANNELS:
        new_found.extend(get_tg_posts(ch))

    # Объединение без дублей
    existing_ids = {p['id'] for p in archive}
    for np in new_found:
        if np['id'] not in existing_ids:
            archive.append(np)

    # Сортировка (свежие сверху)
    archive.sort(key=lambda x: x['date_raw'], reverse=True)
    
    # Сохраняем (до 1000 постов)
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive[:1000], f, ensure_ascii=False, indent=2)

    # Расчет времени обновления (UTC + 3 часа для МСК)
    msk_now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    update_time = msk_now.strftime("%H:%M")

    # Генерация HTML (код фронтенда остается тем же, меняем только переменную времени)
    # ... (весь блок записи index.html из предыдущего сообщения) ...
