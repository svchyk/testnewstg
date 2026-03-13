import feedparser
from feedgen.feed import FeedGenerator
import datetime

# Список твоих источников
URLS = [
    "https://rsshub.app/telegram/channel/chirpnews",
    "https://rsshub.app/telegram/channel/condottieros",
    "https://rsshub.app/telegram/channel/infantmilitario"
]

def aggregate():
    combined_entries = []

    for url in URLS:
        print(f"Парсим: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            # Добавляем название канала к заголовку для ясности
            entry.channel_title = feed.feed.title
            combined_entries.append(entry)

    # Сортируем все новости по дате (сначала свежие)
    combined_entries.sort(key=lambda x: x.get('published_parsed') or x.get('updated_parsed'), reverse=True)

    # Ограничиваем список (например, последние 50 новостей)
    combined_entries = combined_entries[:50]

    # Создаем новый RSS фид
    fg = FeedGenerator()
    fg.title('Моя общая лента новостей')
    fg.link(href='https://github.com', rel='alternate')
    fg.description('Агрегатор новостей из Telegram каналов')

    for entry in combined_entries:
        fe = fg.add_entry()
        fe.title(f"[{entry.channel_title}] {entry.title}")
        fe.link(href=entry.link)
        fe.description(entry.description)
        fe.pubDate(entry.published if 'published' in entry else datetime.datetime.now(datetime.timezone.utc))

    # Сохраняем как RSS файл
    fg.rss_file('rss_combined.xml')

    # Генерируем простой HTML для просмотра в браузере
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write('<html><head><meta charset="utf-8"><title>News Feed</title>')
        f.write('<style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:20px;background:#f4f4f4;} .item{background:#fff;padding:15px;margin-bottom:10px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);}</style>')
        f.write('</head><body><h1>Общая лента новостей</h1>')
        for entry in combined_entries:
            f.write(f'<div class="item"><h3><a href="{entry.link}">{entry.title}</a></h3>')
            f.write(f'<p style="color:gray; font-size:0.8em;">Источник: {entry.channel_title} | Дата: {entry.get("published", "")}</p>')
            f.write(f'<div>{entry.description}</div></div>')
        f.write('</body></html>')

if __name__ == "__main__":
    aggregate()
