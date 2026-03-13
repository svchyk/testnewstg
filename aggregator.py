import feedparser
import datetime
from feedgen.feed import FeedGenerator

# Список твоих каналов (используем rss.app как запасной или t.me напрямую через мост)
# Я подготовил ссылки через другой надежный мост
CHANNELS = [
    "https://rsshub.app/telegram/channel/chirpnews",
    "https://rsshub.app/telegram/channel/condottieros",
    "https://rsshub.app/telegram/channel/infantmilitario"
]

def aggregate():
    combined_entries = []
    
    for url in CHANNELS:
        print(f"Парсим: {url}")
        # Пытаемся получить данные
        feed = feedparser.parse(url)
        
        if not feed.entries:
            print(f"Пусто для канала: {url}")
            continue
            
        for entry in feed.entries:
            # Пытаемся достать чистое имя канала из фида
            source_name = feed.feed.get('title', url.split('/')[-1])
            entry.channel_title = source_name
            combined_entries.append(entry)

    # Если совсем ничего не нашлось, добавим тестовую запись, чтобы страница не была пустой
    if not combined_entries:
        print("Данные не найдены, создаю тестовую запись")
        class TestEntry:
            title = "Лента обновляется..."
            link = "#"
            description = "Пока новых постов нет или сервис временно недоступен. Проверьте через 15 минут."
            channel_title = "Система"
            published = str(datetime.datetime.now())
        combined_entries.append(TestEntry())

    # Сортировка по времени
    combined_entries.sort(key=lambda x: getattr(x, 'published_parsed', 0) or 0, reverse=True)
    combined_entries = combined_entries[:50]

    # Генерация RSS
    fg = FeedGenerator()
    fg.title('My Telegram Feed')
    fg.link(href='https://github.com')
    fg.description('Combined feed')
    for e in combined_entries:
        fe = fg.add_entry()
        fe.title(f"[{getattr(e, 'channel_title', 'TG')}] {e.title[:80]}")
        fe.link(href=e.link)
        fe.description(getattr(e, 'description', ''))

    fg.rss_file('rss_combined.xml')

    # Генерация HTML
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write('<html><head><meta charset="utf-8"><title>News Feed</title>')
        f.write('<style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:20px;background:#f4f4f4;} .item{background:#fff;padding:15px;margin-bottom:10px;border-radius:8px;}</style>')
        f.write('</head><body><h1>Общая лента новостей</h1>')
        f.write(f'<p style="color:gray">Последнее обновление: {datetime.datetime.now().strftime("%H:%M:%S")}</p>')
        for e in combined_entries:
            f.write(f'<div class="item"><h3><a href="{e.link}">{e.title}</a></h3>')
            f.write(f'<p><b>{getattr(e, "channel_title", "")}</b></p>')
            f.write(f'<div>{getattr(e, "description", "")}</div></div>')
        f.write('</body></html>')

if __name__ == "__main__":
    aggregate()
