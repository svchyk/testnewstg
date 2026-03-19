import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re
import yfinance as yf
import logging
from typing import Optional

# Новый SDK: pip install google-genai
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# ==========================================
# 1. КОНФИГУРАЦИЯ
# ==========================================

DISPLAY_CHANNELS  = ['chirpnews', 'condottieros', 'infantmilitario', 'victorstepanych', 'varlamov_news']
ANALYSIS_CHANNELS = ['tasnim_khabar', 'farsna', 'Military_Arabic', 'intelsky', 'war_monitor']

ARCHIVE_FILE = 'archive.json'
GEMINI_KEY   = os.getenv("GEMINI_API_KEY")

# Порядок предпочтения моделей
PREFERRED_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
]

# Инициализируем клиент (без тест-запроса — не тратим квоту)
gemini_client = None

if GEMINI_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_KEY)
        log.info(f"Gemini client initialised. Will try models: {PREFERRED_MODELS}")
    except Exception as e:
        log.error(f"Gemini client init failed: {e}")
else:
    log.warning("GEMINI_API_KEY not set — AI block disabled.")

# ==========================================
# 2. СБОР ДАННЫХ
# ==========================================

def get_oil_price():
    try:
        oil   = yf.Ticker("BZ=F")
        price = oil.history(period="1d")["Close"].iloc[-1]
        return f"{price:.2f}"
    except Exception as e:
        log.warning(f"Oil price error: {e}")
        return "N/A"


def get_reddit_rumors():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(
            "https://www.reddit.com/r/MiddleEastNews/new.json?limit=15",
            headers=headers, timeout=10
        )
        res.raise_for_status()
        posts = res.json()["data"]["children"]
        return " | ".join(p["data"]["title"] for p in posts)
    except Exception as e:
        log.warning(f"Reddit rumors error: {e}")
        return ""


def get_tg_posts(channel_name, limit=100):
    posts   = []
    url     = f"https://t.me/s/{channel_name}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.encoding = "utf-8"
        if response.status_code != 200:
            log.warning(f"Channel {channel_name}: HTTP {response.status_code}")
            return []

        soup      = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("div", class_="tgme_channel_info_header_title")
        full_name = title_tag.text.strip() if title_tag else channel_name

        items = soup.find_all("div", class_="tgme_widget_message_wrap", limit=limit)
        for item in items:
            text_area = item.find("div", class_="tgme_widget_message_text")
            if not text_area:
                continue

            content_html = text_area.decode_contents().strip()
            content_html = re.sub(
                r'<a[^>]*tgme_widget_message_text_more[^>]*>.*?</a>', "", content_html
            )

            link_area = item.find("a", class_="tgme_widget_message_date")
            date_area = item.find("time", class_="time")
            if not link_area:
                continue

            video_url = ""
            video_tag = item.find("video")
            if video_tag:
                video_url = video_tag.get("src", "")

            media_url = ""
            photo       = item.find("a", class_="tgme_widget_message_photo_wrap")
            video_thumb = item.find("i", class_="tgme_widget_message_video_thumb")
            elem  = photo or video_thumb
            style = elem.get("style", "") if elem else ""
            if "url('" in style:
                media_url = style.split("url('")[1].split("')")[0]

            posts.append({
                "id":         f"{channel_name}_{link_area.get('href', '').split('/')[-1]}",
                "full_name":  full_name,
                "content":    content_html,
                "text_plain": text_area.get_text(separator=" "),
                "date_raw":   date_area.get("datetime") if date_area else "",
                "link":       link_area.get("href", ""),
                "handle":     channel_name,
                "media":      media_url,
                "video":      video_url,
            })
    except Exception as e:
        log.error(f"Error scraping {channel_name}: {e}")
    return posts

# ==========================================
# 3. AI-АНАЛИЗ
# ==========================================

_DEFAULT_AI = {
    "escalation":    "N/A",
    "nuclear_risk":  "N/A",
    "ground_op":     "N/A",
    "iran_chance":   "N/A",
    "forecast_date": "N/A",
    "analysis":      "AI-анализ недоступен. Проверьте GEMINI_API_KEY, квоту и подключение к сети.",
    "rumors_block":  "Данные о слухах не получены.",
}

_JSON_SCHEMA = """{
  "escalation":    "<X%>",
  "nuclear_risk":  "<X%>",
  "ground_op":     "<X%>",
  "iran_chance":   "<X%>",
  "forecast_date": "<DD.MM или не определено>",
  "analysis":      "<12 информативных предложений о стратегической ситуации>",
  "rumors_block":  "<10 предложений о трендах в соцсетях и неподтверждённых данных>"
}"""


def _extract_json(text):
    """Надёжно извлекает первый JSON-объект из произвольного текста."""
    text = re.sub(r"```(?:json)?", "", text).strip()

    start = text.find("{")
    if start == -1:
        return None

    depth, end = 0, -1
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return None

    raw = text[start: end + 1]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    try:
        return json.loads(raw.replace("'", '"'))
    except json.JSONDecodeError:
        pass

    log.warning("JSON extraction failed. Snippet: %s", raw[:200])
    return None


def get_ai_analysis(ai_context, oil_info, rumors_info):
    if gemini_client is None:
        return _DEFAULT_AI.copy()

    prompt = (
        "You are a geopolitical intelligence analyst.\n"
        "Analyze the following Middle East news feed and return ONLY a valid JSON object "
        "- no extra text, no markdown, no explanation.\n\n"
        "NEWS FEED:\n" + ai_context[:7000] + "\n\n"
        "BRENT OIL: " + oil_info + " USD/barrel\n"
        "SOCIAL MEDIA RUMORS: " + rumors_info[:1000] + "\n\n"
        "Return this exact JSON structure:\n" + _JSON_SCHEMA + "\n\n"
        "Rules:\n"
        "- Percentages must be realistic (e.g. '34%'). Do NOT use '??%'.\n"
        "- forecast_date: DD.MM format, or 'не определено'.\n"
        "- analysis: exactly 12 sentences.\n"
        "- rumors_block: exactly 10 sentences.\n"
        "- Output ONLY the JSON object, nothing else."
    )

    for model_name in PREFERRED_MODELS:
        for attempt in range(1, 3):
            try:
                log.info("AI request: model=%s attempt=%d", model_name, attempt)
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.4,
                        max_output_tokens=1500,
                    )
                )
                text = response.text.strip()
                data = _extract_json(text)
                if data:
                    required = {"escalation", "nuclear_risk", "ground_op", "iran_chance",
                                "forecast_date", "analysis", "rumors_block"}
                    missing = required - data.keys()
                    if missing:
                        log.warning("Missing keys: %s. Merging with defaults.", missing)
                        merged = _DEFAULT_AI.copy()
                        merged.update(data)
                        return merged
                    log.info("AI analysis OK. model=%s", model_name)
                    return data
                else:
                    log.warning("Could not extract JSON. model=%s attempt=%d", model_name, attempt)

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower():
                    log.warning("Quota exceeded for %s. Trying next model.", model_name)
                    break
                elif "404" in err_str or "not found" in err_str.lower():
                    log.warning("Model %s not found. Trying next model.", model_name)
                    break
                else:
                    log.error("Attempt %d error (%s): %s", attempt, model_name, e)

    log.error("All AI attempts failed. Using defaults.")
    return _DEFAULT_AI.copy()

# ==========================================
# 4. АГРЕГАЦИЯ
# ==========================================

def aggregate():
    archive = []
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                archive = json.load(f)
        except Exception as e:
            log.warning("Could not load archive: %s", e)

    all_scraped = []
    for ch in DISPLAY_CHANNELS:
        posts = get_tg_posts(ch, limit=50)
        log.info("  %s: %d posts", ch, len(posts))
        all_scraped.extend(posts)

    new_posts_sorted = sorted(all_scraped, key=lambda x: x["date_raw"], reverse=True)

    ai_context = "NEWS FEED:\n" + " ".join(p["text_plain"] for p in new_posts_sorted[:50])
    for ch in ANALYSIS_CHANNELS:
        extra = get_tg_posts(ch, limit=10)
        ai_context += " " + " ".join(p["text_plain"] for p in extra)

    oil_info    = get_oil_price()
    rumors_info = get_reddit_rumors()
    log.info("Oil: %s | Rumors chars: %d", oil_info, len(rumors_info))

    ai_data = get_ai_analysis(ai_context, oil_info, rumors_info)
    log.info("AI result: escalation=%s nuclear=%s", ai_data["escalation"], ai_data["nuclear_risk"])

    existing_ids = {p["id"] for p in archive}
    for post in all_scraped:
        if post["id"] not in existing_ids:
            archive.append(post)
    archive.sort(key=lambda x: x["date_raw"], reverse=True)
    archive = archive[:2000]

    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)
    log.info("Archive saved: %d posts", len(archive))

    build_time = (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    ).strftime("%H:%M")

    html_template = """<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <title>Intelligence Center</title>
    <style>
        :root { --bg:#f2f2f7; --card:#fff; --text:#000; --accent:#007aff; --sub:rgba(120,120,128,0.08); }
        [data-theme="dark"] { --bg:#000; --card:#1c1c1e; --text:#fff; --accent:#0a84ff; --sub:rgba(255,255,255,0.06); }
        * { box-sizing:border-box; }
        body { background:var(--bg); color:var(--text); font-family:-apple-system,system-ui,sans-serif; margin:0; padding-bottom:100px; -webkit-tap-highlight-color:transparent; }
        header { position:sticky; top:0; z-index:1000; background:rgba(255,255,255,0.85); backdrop-filter:blur(20px); padding:15px 20px; border-bottom:.5px solid rgba(0,0,0,.1); display:flex; justify-content:space-between; align-items:center; }
        [data-theme="dark"] header { background:rgba(0,0,0,.85); }
        .summary-card { background:var(--card); border-radius:25px; padding:25px; margin:15px; box-shadow:0 10px 30px rgba(0,0,0,.05); }
        .stat-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
        .stat-box { background:var(--sub); padding:12px; border-radius:15px; font-size:11px; font-weight:600; display:flex; flex-direction:column; }
        .stat-val { font-size:18px; font-weight:800; color:var(--accent); margin-top:5px; }
        .card { background:var(--card); border-radius:20px; padding:20px; margin:15px; box-shadow:0 4px 15px rgba(0,0,0,.03); overflow:hidden; }
        .media-container { width:calc(100% + 40px); margin:-20px -20px 15px -20px; background:#000; }
        .media-img, video { width:100%; display:block; max-height:80vh; object-fit:contain; }
        .content { line-height:1.5; font-size:16px; word-wrap:break-word; }
        .tabs { position:fixed; bottom:0; width:100%; background:var(--card); display:flex; padding:12px 0 35px; border-top:.5px solid rgba(0,0,0,.1); z-index:1000; }
        .tab { flex:1; text-align:center; text-decoration:none; color:#8e8e93; font-size:10px; font-weight:700; cursor:pointer; }
        .tab.active { color:var(--accent); }
        .refresh-btn { background:var(--accent); color:#fff; border:none; padding:10px 16px; border-radius:12px; font-size:11px; font-weight:800; cursor:pointer; }
        .rumors-section { margin-top:20px; padding:15px; background:rgba(255,149,0,.08); border-left:4px solid #ff9500; border-radius:10px; font-size:14px; line-height:1.6; }
        .post-time { opacity:.6; font-size:13px; font-weight:700; background:var(--sub); padding:4px 10px; border-radius:10px; }
    </style>
</head>
<body>
<header>
    <h1 style="margin:0;font-size:24px;font-weight:900;">Intelligence</h1>
    <button onclick="toggleTheme()" style="background:none;border:none;font-size:20px;cursor:pointer;">&#127763;</button>
</header>
<div id="main-content" style="max-width:600px;margin:0 auto;">
  <div class="summary-card">
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:20px;border-bottom:1px solid rgba(0,0,0,.1);padding-bottom:10px;">
      <h2 style="margin:0;font-size:16px;letter-spacing:-.5px;font-weight:900;">
        STRATEGIC AI SUMMARY
        <span style="background:var(--accent);color:#fff;padding:2px 6px;border-radius:4px;font-size:9px;">G2</span>
      </h2>
      <div style="text-align:right">
        <span style="font-size:11px;opacity:.5;display:block;font-weight:700;">LAST UPDATE</span>
        <span style="font-size:15px;font-weight:900;color:var(--accent);">_TIME_ MSK</span>
      </div>
    </div>
    <div class="stat-grid">
      <div class="stat-box">Эскалация<span class="stat-val">_ESC_</span></div>
      <div class="stat-box">Ядерный риск<span class="stat-val">_NUC_</span></div>
      <div class="stat-box">Наземная операция<span class="stat-val">_GND_</span></div>
      <div class="stat-box">Шанс Ирана<span class="stat-val">_IRAN_</span></div>
      <div class="stat-box" style="grid-column:span 2;border:1px solid rgba(0,122,255,.2);flex-direction:row;align-items:center;justify-content:space-between;padding:15px;">
        Прогноз наземной операции: <span class="stat-val" style="margin:0;color:var(--accent);">_DATE_</span>
      </div>
    </div>
    <div style="margin-top:20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
        <h3 style="margin:0;font-size:16px;">Глобальный анализ ситуации</h3>
        <button onclick="location.reload()" class="refresh-btn">REFRESH</button>
      </div>
      <div style="font-size:15px;line-height:1.7;opacity:.9;">_ANALYSIS_</div>
      <div class="rumors-section">
        <strong style="color:#ff9500;font-size:12px;text-transform:uppercase;">Мониторинг слухов (X/Reddit):</strong><br>
        <div style="margin-top:5px;opacity:.9;">_RUMORS_</div>
      </div>
    </div>
  </div>
  <div id="feed"></div>
</div>
<div class="tabs">
  <a class="tab active" onclick="render('all',this)">&#128240;<br>СВОДКА</a>
  <a class="tab" onclick="render('archive',this)">&#128230;<br>АРХИВ</a>
  <a class="tab" onclick="render('fav',this)">&#11088;<br>SAVED</a>
</div>
<script>
const allPosts=_JSON_DATA_;
let favorites=JSON.parse(localStorage.getItem('favs')||'[]');
function toggleTheme(){
  const t=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
  document.documentElement.setAttribute('data-theme',t);
  localStorage.setItem('theme',t);
}
function render(mode,el){
  mode=mode||'all';
  if(el){document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});el.classList.add('active');}
  var c=document.getElementById('feed');
  var posts=mode==='all'?allPosts.slice(0,50):mode==='archive'?allPosts.slice(50,500):allPosts.filter(function(p){return favorites.includes(p.id);});
  c.innerHTML=posts.map(function(p){
    var media=p.video?'<div class="media-container"><video src="'+p.video+'" autoplay muted loop playsinline controls></video></div>':p.media?'<div class="media-container"><img src="'+p.media+'" loading="lazy" class="media-img"></div>':'';
    var time=p.date_raw?new Date(p.date_raw).toLocaleString('ru-RU',{hour:'2-digit',minute:'2-digit'}):'';
    var star=favorites.includes(p.id)?'&#11088;':'&#9734;';
    return '<div class="card" id="card-'+p.id+'">'+media+'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;"><a href="'+p.link+'" target="_blank" style="font-weight:800;color:var(--accent);text-decoration:none;line-height:1.3;"><span style="font-size:17px;">'+p.full_name+'</span><br><span style="opacity:.5;font-size:12px;font-weight:400;">@'+p.handle+'</span></a><span class="post-time">'+time+'</span></div><div class="content">'+p.content+'</div><button style="background:none;border:none;cursor:pointer;font-size:24px;margin-top:15px;" onclick="toggleFav(\''+p.id+'\')">'+star+'</button></div>';
  }).join('');
  initVideoObserver();
}
function toggleFav(id){
  favorites=favorites.includes(id)?favorites.filter(function(f){return f!==id;}):[].concat(favorites,[id]);
  localStorage.setItem('favs',JSON.stringify(favorites));
  var m=document.querySelector('.tab.active').textContent;
  render(m.includes('SAVED')?'fav':m.includes('АРХИВ')?'archive':'all');
}
function initVideoObserver(){
  var obs=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.play().catch(function(){});}else{e.target.pause();}});},{threshold:0.5});
  document.querySelectorAll('video').forEach(function(v){obs.observe(v);});
}
document.documentElement.setAttribute('data-theme',localStorage.getItem('theme')||'light');
render();
</script>
</body>
</html>"""

    html = html_template.replace("_TIME_",     build_time)
    html = html.replace("_ESC_",               ai_data["escalation"])
    html = html.replace("_NUC_",               ai_data["nuclear_risk"])
    html = html.replace("_GND_",               ai_data["ground_op"])
    html = html.replace("_IRAN_",              ai_data["iran_chance"])
    html = html.replace("_DATE_",              ai_data["forecast_date"])
    html = html.replace("_ANALYSIS_",          ai_data["analysis"])
    html = html.replace("_RUMORS_",            ai_data["rumors_block"])
    html = html.replace("_JSON_DATA_",         json.dumps(archive, ensure_ascii=False))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    log.info("index.html written successfully.")


if __name__ == "__main__":
    aggregate()
