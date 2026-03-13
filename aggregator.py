import requests
from bs4 import BeautifulSoup
import datetime

# Список только имен каналов (без t.me/)
CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']

def get_tg_posts(channel_name):
    posts = []
    # Прямой адрес веб-витрины Телеграма
    url = f"https://t.me/s/{channel_name}"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем блоки с сообщениями
        items = soup.find_all('div', class_='tgme_widget_message_wrap', limit=10)
        
        for item in items:
            text_area = item.find('div', class_='tgme_widget_message_text')
            date_area = item.find('time', class_='time')
            link_area = item.find('a', class_='tgme_widget_message_date')
            
            if text_area:
                posts.append({
                    'title': text_area.text[:80] + '...',
                    'content': str(text_area),
                    'date': date_area.get('datetime') if date_area else '',
                    'link': link_area.get('href') if link_area else f"https://t.me/{channel_name}",
                    'source': channel_name
                })
    except Exception as e:
        print(f"Ошибка при чтении {channel_name}: {e}")
    return posts

def aggregate():
    all_posts = []
    for ch in CHANNELS:
        print(f"Читаю напрямую: {ch}")
        all_posts.extend(get_tg_posts(ch))

    # Сортировка по дате (если она есть)
    all_posts.sort(key=lambda x: x['date'], reverse=True)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write('''<html><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; background: #f4f7f9; max-width: 600px; margin: 0 auto; padding: 20px; }
            .card { background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .source { color: #0088cc; font-weight: bold; font-size: 0.9em; }
            .date { color: #999; font-size: 0.8em; float: right; }
            a { text-decoration: none; color: #333; }
        </style></head><body>''')
        
        f.write(f'<h1>Прямая лента Telegram</h1><p>Обновлено: {datetime.datetime.now().strftime("%H:%M")}</p>')
        
        for p in all_posts[:30]:
            f.write(f'<div class="card">')
            f.write(f'<span class="source">@{p["source"]}</span>')
            f.write(f'<span class="date">{p["date"][:10] if p["date"] else ""}</span>')
            f.write(f'<h3><a href="{p["link"]}" target="_blank">{p["title"]}</a></h3>')
            f.write(f'<div>{p["content"]}</div>')
            f.write('</div>')
            
        f.write('</body></html>')

if __name__ == "__main__":
    aggregate()
