import os
import feedparser
import datetime

# Получаем данные из секретов GitHub
# Убедись, что в Settings -> Secrets они названы именно так!
api_id = os.getenv('TG_API_ID')
api_hash = os.getenv('TG_API_HASH')

CHANNELS = [
    "https://rsshub.app/telegram/channel/chirpnews",
    "https://rsshub.app/telegram/channel/condottieros",
    "https://rsshub.app/telegram/channel/infantmilitario"
]

def aggregate():
    if not api_id or not api_hash:
        print(f"DEBUG: ID={api_id}, HASH={'set' if api_hash else 'None'}")
        # Если секреты не подхватились, мы все равно попробуем скачать новости
        # просто через RSS мост, чтобы страница не была пустой.
    
    items = []
    for url in CHANNELS:
        print(f"Пытаюсь загрузить: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            items.append({
                'title': entry.title,
                'link': entry.link,
                'desc': entry.description,
                'source': feed.feed.title if 'title' in feed.feed else 'Telegram',
                'dt': entry.get('published', 'Недавно')
            })
    
    # Создаем HTML
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write('<html><head><meta charset="utf-8"><style>body{font-family:sans-serif;max-width:700px;margin:auto;background:#f9f9f9;padding:20px;} .card{background:#fff;padding:15px;margin-bottom:15px;border-radius:10px;box-shadow:0 2px 5px rgba(0,0,0,0.05);} img{max-width:100%;height:auto;}</style></head><body>')
        f.write(f'<h1>Лента новостей</h1><p>Обновлено: {datetime.datetime.now().strftime("%H:%M:%S")}</p>')
        
        if not items:
            f.write('<p>Данные пока не получены. Возможно, сервис временно занят. Попробуйте через 10 минут.</p>')
        
        for i in items[:50]:
            f.write(f'<div class="card">')
            f.write(f'<small style="color:blue">{i["source"]} | {i["dt"]}</small>')
            f.write(f'<h3><a href="{i["link"]}">{i["title"]}</a></h3>')
            f.write(f'<div>{i["desc"]}</div>')
            f.write('</div>')
        f.write('</body></html>')

if __name__ == "__main__":
    aggregate()
