import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re

# ==========================================
# СПИСОК КАНАЛОВ И НАСТРОЙКИ
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
        
        # Глубина парсинга — до 100 постов
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=100)
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            if not text_area: continue
            
            # Захват полного текста без "Read more"
            content_html = text_area.decode_contents().strip()
            content_html = re.sub(r'<a[^>]*tgme_widget_message_text_more[^>]*>.*?</a>', '', content_html)
            
            link_area = item.find('a', class_='tgme_widget_message_date')
            date_area = item.find('time', class_='time')
            if not link_area: continue

            # Обработка видео и фото
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
    # Берем последние 100 постов для анализа
    analysis_pool = [p['text_plain'].lower() for p in all_posts[:100]]
    
    def find_info(keywords, default_text):
        for text in analysis_pool:
            for word in keywords:
                if word in text:
                    sentences = re.split(r'[.!?]', text)
                    for s in sentences:
                        if word in s.lower() and len(s) > 10:
                            return s.strip().capitalize() + "."
        return default_text

    # Сборка данных для 13 пунктов
    summary_data = {
        "изменения": find_info(["ударов", "взрыв", "атака", "переброс", "сводка"], "За последние 3 часа значительных изменений в линии соприкосновения не зафиксировано."),
        "иран_успех": find_info(["пво", "сбил", "поразил", "рлс", "успешно"], "О новых успехах ПВО Ирана за текущий период сообщений нет."),
        "пролив": find_info(["пролив", "танкер", "судно", "мин", "вмс"], "Судоходство в Ормузском проливе продолжается без экстраординарных инцидентов."),
        "факты": find_info(["подтверждено", "факт", "официально", "заявил"], "Официальные источники подтверждают стабильность текущих позиций."),
        "слухи": find_info(["сообщают", "пишут", "возможно", "источники"], "В мониторинговых каналах обсуждается вероятная подготовка к учениям."),
        "рынки": find_info(["нефть", "доллар", "brent", "биржа", "цена"], "Рынок энергоносителей сохраняет умеренную волатильность."),
        "дубай": find_info(["дубай", "аэропорт", "рейс", "эмираты"], "В Дубае и ОАЭ обстановка остается стабильной, порты работают штатно."),
        "россия": find_info(["лавров", "песков", "кремль", "мид", "рф"], "Дипломатический корпус РФ призывает к деэскалации в рабочем порядке."),
        "неочевидное": find_info(["заметили", "аномально", "странно", "gps"], "Локальные сбои в навигации в северных районах."),
        "мобилизация": find_info(["призыв", "мобилиз", "резервист", "добровол"], "Масштабных призывных мероприятий в И
