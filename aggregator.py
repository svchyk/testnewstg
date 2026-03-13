import os
import datetime
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from feedgen.feed import FeedGenerator

# Настройки из секретов GitHub
api_id = os.getenv('TG_API_ID')
api_hash = os.getenv('TG_API_HASH')

CHANNELS = ['chirpnews', 'condottieros', 'infantmilitario']

def aggregate():
    combined_entries = []
    
    # Сессия будет создаваться каждый раз заново в GitHub Actions
    with TelegramClient('anon', api_id, api_hash) as client:
        for channel in CHANNELS:
            print(f"Читаю канал: {channel}")
            try:
                # Берем последние 15 постов из каждого канала
                posts = client.get_messages(channel, limit=15)
                
                for post in posts:
                    if post.message: # Только текстовые сообщения
                        combined_entries.append({
                            'title': post.message[:80] + '...',
                            'desc': post.message,
                            'date': post.date,
                            'link': f"https://t.me/{channel}/{post.id}",
                            'channel': channel
                        })
            except Exception as e:
                print(f"Ошибка с каналом {channel}: {e}")

    # Сортировка: свежие сверху
    combined_entries.sort(key=lambda x: x['date'], reverse=True)

    # Генерируем HTML
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write('<html><head><meta charset="utf-8"><style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:20px;background:#f0f2f5;} .item{background:#fff;padding:20px;margin-bottom:15px;border-radius:12px;box-shadow:0 2px 5px rgba(0,0,0,0.1);}</style></head><body>')
        f.write(f'<h1>Общая лента (прямое чтение)</h1><p>Обновлено: {datetime.datetime.now().strftime("%H:%M:%S")}</p>')
        
        for e in combined_entries[:50]:
            f.write(f'<div class="item">')
            f.write(f'<small>{e["channel"]} | {e["date"].strftime("%d.%m %H:%M")}</small>')
            f.write(f'<h3><a href="{e["link"]}">{e["title"]}</a></h3>')
            f.write(f'<div>{e["desc"][:500]}...</div>')
            f.write('</div>')
        f.write('</body></html>')

if __name__ == "__main__":
    if api_id and api_hash:
        aggregate()
    else:
        print("Ошибка: API_ID или API_HASH не настроены в Secrets!")
