import feedparser
import datetime

# Используем список разных зеркал для надежности
SOURCES = [
    "https://rsshub.app/telegram/channel/chirpnews",
    "https://rsshub.app/telegram/channel/condottieros",
    "https://rsshub.app/telegram/channel/infantmilitario",
    # Если rsshub не сработает, в будущем сюда можно добавить ссылки от других сервисов
]

def aggregate():
    all_items = []
    
    for url in SOURCES:
        print(f"Запрос к: {url}")
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print(f"Источник {url} пуст или заблокирован.")
            continue
            
        for entry in feed.entries:
            all_items.append({
                'title': entry.get('title', 'Без заголовка'),
                'link': entry.get('link', '#'),
                'desc': entry.get('description', ''),
                'source': feed.feed.get('title', url.split('/')[-1]),
                'date': entry.get('published', '')
            })

    # Сортируем (если есть дата)
    all_items = all_items[:60]

    # Генерируем HTML с более современным дизайном
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write('''
        <html><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: -apple-system, sans-serif; background: #eef2f5; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
            h1 { text-align: center; color: #0088cc; }
            .update-time { text-align: center; font-size: 0.8em; color: #777; margin-bottom: 20px; }
            .card { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
            .card small { color: #0088cc; font-weight: bold; text-transform: uppercase; font-size: 0.7em; }
            .card h3 { margin: 10px 0; font-size: 1.1em; line-height: 1.4; }
            .card a { text-decoration: none; color: #222; }
            .card .content { font-size: 0.95em; line-height: 1.5; color: #444; }
            .card .content img { max-width: 100%; border-radius: 10px; margin-top: 10px; }
        </style></head><body>
        ''')
        
        f.write(f'<h1>TG News Feed</h1>')
        f.write(f'<div class="update-time">Обновлено: {datetime.datetime.now().strftime("%d.%m %H:%M:%S")}</div>')
        
        if not all_items:
            f.write('<div class="card" style="text-align:center;"><h3>Пока пусто</h3><p>Telegram временно ограничил доступ. Скрипт попробует снова через 15 минут автоматически.</p></div>')
        
        for item in all_items:
            f.write(f'<div class="card">')
            f.write(f'<small>{item["source"]}</small>')
            f.write(f'<h3><a href="{item["link"]}" target="_blank">{item["title"]}</a></h3>')
            f.write(f'<div class="content">{item["desc"]}</div>')
            f.write(f'</div>')
            
        f.write('</body></html>')

if __name__ == "__main__":
    aggregate()
