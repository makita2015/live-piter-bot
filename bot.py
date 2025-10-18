#!/usr/bin/env python3
# bot.py - Новостной бот для канала "Live Питер 📸" (компактная версия)
import os
import time
import json
import random
import asyncio
import aiohttp
import re
import signal
import sys
from datetime import datetime
from bs4 import BeautifulSoup
from telebot.async_telebot import AsyncTeleBot
from dotenv import load_dotenv

# Проверка и создание необходимых папок
os.makedirs('./static', exist_ok=True)
print(f"📁 Папка static создана/проверена")

# Загрузка переменных окружения
load_dotenv()

# --- Конфигурация ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@LivePiter")
AUTO_POST_INTERVAL = int(os.getenv("AUTO_POST_INTERVAL", "1800"))
PORT = int(os.getenv("PORT", "10000"))
RENDER_APP_URL = os.getenv("RENDER_APP_URL", "")

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN не установлен")

# Инициализация бота
bot = AsyncTeleBot(BOT_TOKEN)

# --- Глобальная переменная для заглушки ---
DEFAULT_PLACEHOLDER_PATH = './static/placeholder.jpg'

# --- Управление опубликованными новостями ---
def load_posted_news():
    """Загрузка списка опубликованных новостей"""
    try:
        posted_json = os.getenv("POSTED_NEWS", "[]")
        posted_set = set(json.loads(posted_json))
        
        if os.path.exists('posted.json'):
            with open('posted.json', 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                posted_set.update(file_data)
                
        return posted_set
    except Exception as e:
        print(f"⚠️ Ошибка загрузки posted news: {e}")
        return set()

def save_posted_news(posted_news_set):
    """Сохранение списка опубликованных новостей"""
    try:
        posted_list = list(posted_news_set)
        print(f"💾 Сохранено {len(posted_list)} новостей")
        
        os.environ["POSTED_NEWS"] = json.dumps(posted_list)
        
        with open('posted.json', 'w', encoding='utf-8') as f:
            json.dump(posted_list, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"⚠️ Ошибка сохранения posted news: {e}")

posted_news = load_posted_news()

# --- Обработчик остановки ---
def signal_handler(signum, frame):
    print(f"🔻 Получен сигнал {signum}, сохраняем данные...")
    save_posted_news(posted_news)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# --- HTTP сервер для здоровья ---
async def health_server():
    """HTTP сервер для проверки здоровья"""
    from aiohttp import web
    
    async def health_check(request):
        return web.Response(
            text=json.dumps({
                "status": "🟢 Бот работает",
                "sources": len(NEWS_SOURCES),
                "posted": len(posted_news),
                "timestamp": datetime.now().isoformat(),
                "version": "5.0 компактная версия"
            }, ensure_ascii=False),
            content_type='application/json'
        )
    
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🌐 HTTP сервер запущен на порту {PORT}")
    
    return runner

# --- Keep-Alive для Render ---
async def enhanced_keep_alive():
    """Улучшенный keep-alive с внешним пингингом"""
    print("🔄 ЗАПУСК УЛУЧШЕННОГО KEEP-ALIVE...")
    
    while True:
        try:
            # Внутренний пинг
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f'http://localhost:{PORT}/health', timeout=10) as resp:
                        if resp.status == 200:
                            print(f"✅ Внутренний ping: {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                print(f"⚠️ Ошибка внутреннего ping: {e}")
            
            # Внешний PING
            if RENDER_APP_URL:
                try:
                    async with aiohttp.ClientSession() as session:
                        random_param = f"?ping={random.randint(1000,9999)}"
                        async with session.get(f'{RENDER_APP_URL}/health{random_param}', timeout=30) as resp:
                            if resp.status == 200:
                                print(f"🌐 ВНЕШНИЙ PING УСПЕШЕН: {datetime.now().strftime('%H:%M:%S')}")
                except Exception as e:
                    print(f"⚠️ Ошибка внешнего ping: {e}")
            
            # Случайная публикация
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 23:
                if random.random() < 0.3:
                    print("🎰 Случайная активация автопостинга...")
                    try:
                        await publish_news(1)
                    except Exception as e:
                        print(f"⚠️ Ошибка случайного постинга: {e}")
            
        except Exception as e:
            print(f"⚠️ Общая ошибка keep-alive: {e}")
        
        sleep_time = random.randint(480, 600)
        print(f"💤 Следующий keep-alive через {sleep_time} секунд...")
        await asyncio.sleep(sleep_time)

# --- Улучшенный парсинг для законченных новостей ---
def extract_complete_text_from_html(html_content, title):
    """Извлечение полного текста новости"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Удаляем ненужные элементы
        for element in soup(['script', 'style', 'nav', 'footer', 'aside', 'header', 'form', 'button', 'iframe']):
            element.decompose()
        
        # Приоритетные селекторы для контента
        content_selectors = [
            'article',
            '.article',
            '.content', 
            '.news-content',
            '.post-content',
            '.text',
            '.news-text',
            '.story__content',
            '.b-article__content',
            '.js-article-content',
            '[class*="content"]',
            '[class*="article"]',
            '[class*="post"]',
            '[class*="story"]'
        ]
        
        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break
        
        if not content_element:
            content_element = soup.find('body') or soup
        
        # Собираем все значимые элементы текста
        text_elements = content_element.find_all(['p', 'div', 'h2', 'h3'])
        meaningful_paragraphs = []
        
        for element in text_elements:
            text = element.get_text().strip()
            # Фильтрация
            if (len(text) > 40 and 
                not any(x in text for x in [
                    '©', 'Фото:', 'Источник:', 'Читайте также:', 'Редакция',
                    'Комментарии', 'Подпишитесь', 'Rambler', 'ТАСС', 
                    'Lenta.ru', 'РИА Новости', 'Поделиться', 'Следите за',
                    'INTERFAX.RU', 'https://', 'http://', 'www.'
                ]) and
                len(text.split()) > 8 and
                not text.startswith('http')):
                meaningful_paragraphs.append(text)
        
        # Берем только 2-3 первых значимых абзаца
        if meaningful_paragraphs:
            selected_paragraphs = meaningful_paragraphs[:3]  # Только 2-3 абзаца
            full_text = '\n\n'.join(selected_paragraphs)
            
            if len(full_text.split()) < 50:
                full_text = f"{title}\n\n{full_text}"
            
            return full_text[:3000]  # Стандартный лимит
            
    except Exception as e:
        print(f"⚠️ Ошибка парсинга HTML: {e}")
    
    return ""

def remove_duplicate_text(text):
    """Удаление дублированного текста из новости"""
    if not text:
        return text
    
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    unique_sentences = []
    seen_sentences = set()
    
    for sentence in sentences:
        normalized = re.sub(r'\s+', ' ', sentence).strip().lower()
        if normalized and normalized not in seen_sentences:
            seen_sentences.add(normalized)
            unique_sentences.append(sentence)
    
    cleaned_text = '. '.join(unique_sentences) + '.' if unique_sentences else ''
    
    if len(cleaned_text.split()) < 20 and len(text.split()) > 30:
        return text
    
    return cleaned_text

def create_engaging_title(original_title):
    """Создание цепляющего заголовка"""
    clean_title = original_title
    
    # Убираем URL и источники
    clean_title = re.sub(r'https?://\S+|www\.\S+', '', clean_title)
    clean_title = re.sub(r'\b(INTERFAX\.RU|РИА\s*Новости|ТАСС|Lenta\.ru|Rambler)\b', '', clean_title, flags=re.IGNORECASE)
    
    # Убираем дублирующиеся тире и точки
    clean_title = re.sub(r'[–—]\s*[–—]+', '—', clean_title)
    clean_title = re.sub(r'\.\s*\.+', '.', clean_title)
    
    # Удаляем дублированный текст
    clean_title = remove_duplicate_text(clean_title)
    
    # Обрезаем слишком длинные заголовки
    if len(clean_title) > 120:
        sentences = clean_title.split('. ')
        if len(sentences) > 1:
            clean_title = sentences[0] + '.'
        else:
            clean_title = clean_title[:117] + '...'
    
    return clean_title.strip()

def format_news_live_piter_style(title, description, full_text):
    """Форматирование новости в стиле Live Питер 📸 (компактная версия)"""
    # Создаем чистый заголовок
    clean_title = create_engaging_title(title)
    
    # Определяем основной текст - берем только 2-3 абзаца
    if full_text and len(full_text.split()) > 40:
        paragraphs = full_text.split('\n\n')
        
        # Берем максимум 3 абзаца
        if len(paragraphs) >= 2:
            intro = paragraphs[0]
            # Берем только 1-2 дополнительных абзаца
            additional_paragraphs = paragraphs[1:3]  # Только 2-й и 3-й абзац
            formatted_text = f"{intro}\n\n" + "\n\n".join(additional_paragraphs)
        else:
            formatted_text = full_text
    elif description and len(description.split()) > 20:
        formatted_text = description
    else:
        formatted_text = full_text if full_text else description
    
    # Удаляем ссылки и источники
    formatted_text = re.sub(r'https?://\S+|www\.\S+', '', formatted_text)
    formatted_text = re.sub(r'\b(INTERFAX\.RU|РИА\s*Новости|ТАСС|Lenta\.ru|Rambler|Фонтанка\.ру|78\.ру|Каннал7|Петербург2|ДП)\b', '', formatted_text, flags=re.IGNORECASE)
    
    # Удаляем дублированный текст
    formatted_text = remove_duplicate_text(formatted_text)
    
    # Очистка и форматирование
    formatted_text = re.sub(r'\s+', ' ', formatted_text)
    formatted_text = re.sub(r'\.\s+', '.\n\n', formatted_text)
    
    # Собираем финальное сообщение
    final_text = f"{clean_title}\n\n{formatted_text}"
    
    # Убираем лишние пустые строки
    final_text = re.sub(r'\n\s*\n', '\n\n', final_text)
    
    # Обрезаем до стандартных пределов
    if len(final_text) > 3000:
        # Ищем естественное место для обрезки
        cut_position = final_text.rfind('. ', 2500, 3000)
        if cut_position == -1:
            cut_position = final_text.rfind('! ', 2500, 3000)
        if cut_position == -1:
            cut_position = final_text.rfind('? ', 2500, 3000)
        if cut_position == -1:
            cut_position = 2997
        
        final_text = final_text[:cut_position + 1]
    
    return final_text.strip()

# --- Источники новостей ---
NEWS_SOURCES = [
    # Общероссийские источники
    "https://lenta.ru/rss/news",
    "https://tass.ru/rss/v2.xml", 
    "https://news.rambler.ru/rss/world/",
    
    # Санкт-Петербургские источники
    "https://www.fontanka.ru/fontanka.rss",
    "https://78.ru/text/rss.xml",
    "https://kanal7.ru/rss/",
    "https://peterburg2.ru/rss/",
    "https://www.dp.ru/rss/",
    
    # Дополнительные источники
    "https://ria.ru/export/rss2/archive/index.xml",
    "https://www.interfax.ru/rss.asp",
    "https://www.kommersant.ru/RSS/news.xml",
]

# --- Функции работы с новостями ---
def extract_image_from_item(item_soup):
    """Извлечение изображения из RSS элемента"""
    image_sources = [
        lambda: item_soup.find("enclosure"),
        lambda: item_soup.find("media:content"),
        lambda: item_soup.find("media:thumbnail"),
        lambda: item_soup.find("image")
    ]
    
    for source in image_sources:
        try:
            element = source()
            if element and element.get("url"):
                url = element.get("url")
                if url and (url.startswith(('http', '//')) and 
                           any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp'])):
                    return url
        except Exception:
            continue
    return None

def find_og_image(html_content):
    """Поиск Open Graph изображения в HTML"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            url = og_image.get('content')
            if url and any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                return url
    except Exception as e:
        print(f"⚠️ Ошибка поиска OG изображения: {e}")
    return None

async def download_image(session, url):
    """Асинхронное скачивание изображения"""
    if not url:
        return None
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        if not url.startswith('http'):
            if url.startswith('//'):
                url = 'https:' + url
            else:
                return None
        
        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status == 200:
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type:
                    filename = f"./temp_image_{int(time.time())}_{random.randint(1000, 9999)}.jpg"
                    content = await response.read()
                    
                    if len(content) > 10240:
                        with open(filename, 'wb') as f:
                            f.write(content)
                        return filename
                
    except Exception as e:
        print(f"⚠️ Ошибка скачивания изображения {url}: {e}")
    
    return None

async def get_news_from_source(session, source_url, limit=5):
    """Получение новостей из одного источника"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        print(f"🔍 Запрос к: {source_url}")
        async with session.get(source_url, headers=headers, timeout=15) as response:
            if response.status != 200:
                print(f"⚠️ Ошибка {response.status} для {source_url}")
                return []
                
            content = await response.text()
            soup = BeautifulSoup(content, 'xml')
            items = soup.find_all('item')[:limit]
            
            news_items = []
            for item in items:
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    description_elem = item.find('description')
                    
                    if not title_elem or not link_elem:
                        continue
                        
                    title = title_elem.get_text().strip()
                    link = link_elem.get_text().strip()
                    description = ""
                    
                    if description_elem:
                        description = re.sub(r'<[^>]+>', '', description_elem.get_text()).strip()
                    
                    if not title or not link:
                        continue
                    
                    image_url = extract_image_from_item(item)
                    
                    # Если изображения нет в RSS, ищем на странице
                    if not image_url and link:
                        try:
                            async with session.get(link, headers=headers, timeout=8) as page_response:
                                if page_response.status == 200:
                                    page_content = await page_response.text()
                                    image_url = find_og_image(page_content)
                        except Exception as e:
                            print(f"⚠️ Ошибка поиска изображения на странице: {e}")
                    
                    news_items.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'source': source_url,
                        'image': image_url
                    })
                    
                except Exception as e:
                    print(f"⚠️ Ошибка обработки элемента в {source_url}: {e}")
                    continue
            
            print(f"✅ Получено {len(news_items)} новостей из {source_url}")
            return news_items
            
    except Exception as e:
        print(f"❌ Ошибка получения новостей из {source_url}: {e}")
        return []

async def get_all_news(limit_per_source=5):
    """Получение новостей из всех источников"""
    print("🔍 Получение новостей из источников...")
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for source in NEWS_SOURCES:
            task = get_news_from_source(session, source, limit_per_source)
            tasks.append(task)
            await asyncio.sleep(1)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
        
        print(f"✅ Получено {len(all_news)} новостей из {len(NEWS_SOURCES)} источников")
        return all_news

async def get_extended_news_text(link, title, session):
    """Получение расширенного текста новости со страницы"""
    if not link:
        return ""
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        async with session.get(link, headers=headers, timeout=10) as response:
            if response.status == 200:
                html = await response.text()
                return extract_complete_text_from_html(html, title)
                    
    except Exception as e:
        print(f"⚠️ Ошибка получения текста новости: {e}")
    
    return ""

async def prepare_news_item(item):
    """Подготовка новости к публикации"""
    title = item.get('title', 'Без заголовка')
    link = item.get('link', '')
    description = item.get('description', '')
    image_url = item.get('image', '')
    
    print(f"📝 Подготовка: {title[:60]}...")
    
    # Получаем полный текст новости
    news_text = ""
    if link:
        async with aiohttp.ClientSession() as session:
            news_text = await get_extended_news_text(link, title, session)
    
    # Форматируем в стиле Live Питер
    final_text = format_news_live_piter_style(title, description, news_text)
    
    # Проверяем минимальную длину
    word_count = len(final_text.split())
    if word_count < 40:
        print(f"❌ Пропущена новость: '{title[:30]}...' - недостаточно текста ({word_count} слов)")
        return None
    
    print(f"✅ Текст подготовлен: {word_count} слов")
    
    # Работа с изображением
    image_path = None
    
    # Сначала пробуем скачать изображение из новости
    if image_url:
        async with aiohttp.ClientSession() as session:
            image_path = await download_image(session, image_url)
            if image_path:
                print("✅ Используем изображение из новости")
    
    # Если нет изображения из новости - используем заглушку из static
    if not image_path:
        if os.path.exists(DEFAULT_PLACEHOLDER_PATH):
            image_path = DEFAULT_PLACEHOLDER_PATH
            print("✅ Используем заглушку из папки static")
        else:
            print("⚠️ Заглушка не найдена в static, отправляем без изображения")
    
    return {
        'title': title,
        'summary': final_text,
        'link': link,
        'image_path': image_path,
        'word_count': word_count
    }

async def send_news_to_channel(news_item):
    """Отправка новости в канал"""
    try:
        title = news_item['title']
        summary = news_item['summary']
        image_path = news_item['image_path']
        word_count = news_item['word_count']
        
        print(f"📤 Отправка новости: {title[:50]}...")
        
        # Форматируем сообщение
        message_text = summary
        
        if image_path and os.path.exists(image_path):
            print(f"🖼️ Используем изображение: {image_path}")
            try:
                with open(image_path, 'rb') as photo:
                    await bot.send_photo(
                        CHANNEL_ID,
                        photo,
                        caption=message_text,
                        parse_mode='HTML'
                    )
                print("✅ Новость с изображением отправлена")
                
                # Удаляем временные файлы (кроме заглушки из static)
                if 'temp_image_' in image_path:
                    try:
                        os.remove(image_path)
                        print("✅ Временный файл изображения удален")
                    except Exception as e:
                        print(f"⚠️ Не удалось удалить временный файл: {e}")
                        
            except Exception as e:
                print(f"❌ Ошибка отправки с изображением: {e}")
                # Fallback: отправляем только текст
                await bot.send_message(
                    CHANNEL_ID,
                    message_text,
                    parse_mode='HTML'
                )
        else:
            print("ℹ️ Изображение не найдено, отправляем только текст")
            await bot.send_message(
                CHANNEL_ID,
                message_text,
                parse_mode='HTML'
            )
        
        print(f"✅ Опубликовано: {title[:70]}... ({word_count} слов)")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки новости: {e}")
        return False

async def publish_news(count=1):
    """Публикация указанного количества новостей"""
    print(f"🚀 Запуск публикации {count} новостей...")
    
    all_news = await get_all_news()
    if not all_news:
        print("⚠️ Новости не найдены")
        return 0
    
    # Фильтруем только новые новости
    new_news = []
    for item in all_news:
        news_id = item.get('link') or item.get('title')
        if news_id and news_id not in posted_news:
            new_news.append(item)
    
    if not new_news:
        print("ℹ️ Нет новых новостей для публикации")
        return 0
    
    # Перемешиваем для разнообразия
    random.shuffle(new_news)
    
    published_count = 0
    attempts = 0
    max_attempts = min(len(new_news) * 2, 15)
    
    while published_count < count and attempts < max_attempts:
        if attempts >= len(new_news):
            break
            
        item = new_news[attempts]
        attempts += 1
        
        try:
            prepared_item = await prepare_news_item(item)
            
            if prepared_item is None:
                continue
                
            success = await send_news_to_channel(prepared_item)
            
            if success:
                news_id = item.get('link') or item.get('title')
                if news_id:
                    posted_news.add(news_id)
                    published_count += 1
                    save_posted_news(posted_news)
                
                # Задержка между публикациями
                await asyncio.sleep(random.randint(45, 120))
                
        except Exception as e:
            print(f"❌ Ошибка публикации новости: {e}")
            continue
    
    print(f"✅ Опубликовано новостей: {published_count} из {count} запланированных")
    return published_count

# --- Команды бота ---
@bot.message_handler(commands=['start'])
async def send_welcome(message):
    welcome_text = """
🤖 Новостной бот для канала "Live Питер 📸"
КОМПАКТНАЯ ВЕРСИЯ

📰 Источники:
• 3 федеральных новостных портала
• 5 локальных питерских изданий
• 3 дополнительных надежных источника

🎯 Особенности:
• Компактные новости (2-3 абзаца)
• Заглушка из папки static
• Улучшенный keep-alive
• Автопостинг в рабочее время

📋 Команды:
/post - Опубликовать новости
/status - Статус бота  
/stats - Статистика
/sources - Список источников
/wake - Принудительная активация
"""
    await bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['wake'])
async def force_wake(message):
    """Принудительная активация бота"""
    try:
        await bot.reply_to(message, "🔔 Активирую бота...")
        await publish_news(1)
        await bot.reply_to(message, "✅ Бот активирован и опубликовал новость")
    except Exception as e:
        await bot.reply_to(message, f"❌ Ошибка активации: {e}")

@bot.message_handler(commands=['post'])
async def manual_post(message):
    try:
        await bot.reply_to(message, "⏳ Запускаю публикацию новостей...")
        count = random.randint(1, 2)
        published = await publish_news(count)
        await bot.reply_to(message, f"✅ Опубликовано {published} новостей в стиле 'Live Питер 📸'")
    except Exception as e:
        await bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['status'])
async def bot_status(message):
    status_text = f"""
📊 Статус бота (КОМПАКТНАЯ ВЕРСИЯ):

🤖 Бот: Активен
📰 Источников: {len(NEWS_SOURCES)}
📨 Опубликовано: {len(posted_news)}
🎯 Формат: Компактные новости (2-3 абзаца)
⏰ Keep-alive: каждые 8-10 минут
🌐 Внешний ping: {'✅ Включен' if RENDER_APP_URL else '❌ Выключен'}
🖼️ Заглушка: {'✅ В папке static' if os.path.exists(DEFAULT_PLACEHOLDER_PATH) else '❌ Не найдена'}
"""
    await bot.reply_to(message, status_text)

@bot.message_handler(commands=['stats'])
async def bot_stats(message):
    stats_text = f"""
📈 Статистика:

📊 Всего новостей: {len(posted_news)}
🔗 Источники ({len(NEWS_SOURCES)}):
"""
    for source in NEWS_SOURCES:
        source_name = source.split('//')[-1].split('/')[0]
        stats_text += f"   • {source_name}\n"
    
    await bot.reply_to(message, stats_text)

@bot.message_handler(commands=['sources'])
async def show_sources(message):
    sources_text = "📰 Источники новостей:\n\n"
    
    federal = [s for s in NEWS_SOURCES if 'lenta' in s or 'tass' in s or 'rambler' in s or 'ria' in s or 'interfax' in s or 'kommersant' in s]
    local = [s for s in NEWS_SOURCES if s not in federal]
    
    sources_text += "🏛️ Федеральные:\n"
    for source in federal:
        source_name = source.split('//')[-1].split('/')[0]
        sources_text += f"• {source_name}\n"
    
    sources_text += "\n🏙️ Питерские:\n"
    for source in local:
        source_name = source.split('//')[-1].split('/')[0]
        sources_text += f"• {source_name}\n"
    
    await bot.reply_to(message, sources_text)

async def auto_poster():
    """Фоновая задача автоматической публикации"""
    print("🔄 Запуск автоматической публикации...")
    
    while True:
        try:
            # Публикуем в активное время (8:00-23:00)
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 23:
                news_count = random.randint(1, 2)
                print(f"📰 Автопостинг: публикую {news_count} новостей...")
                await publish_news(news_count)
            else:
                print("💤 Ночное время, автопостинг приостановлен")
            
            # Случайный интервал 25-40 минут
            sleep_time = random.randint(1500, 2400)
            print(f"⏳ Следующая проверка через {sleep_time//60} минут...")
            await asyncio.sleep(sleep_time)
            
        except Exception as e:
            print(f"⚠️ Ошибка в авто-постинге: {e}")
            await asyncio.sleep(600)

async def main():
    """Основная функция запуска бота"""
    print("🚀 Запуск новостного бота 'Live Питер 📸' (КОМПАКТНАЯ ВЕРСИЯ)...")
    print(f"📰 Источников: {len(NEWS_SOURCES)}")
    print(f"🎯 Формат: компактные новости (2-3 абзаца)")
    print(f"⏰ Keep-alive: каждые 8-10 минут")
    print(f"🌐 Внешний URL: {RENDER_APP_URL or 'Не установлен'}")
    print(f"📺 Канал: {CHANNEL_ID}")
    print(f"🖼️ Заглушка: {DEFAULT_PLACEHOLDER_PATH}")
    
    # Проверяем наличие заглушки
    if not os.path.exists(DEFAULT_PLACEHOLDER_PATH):
        print("⚠️ ВНИМАНИЕ: Заглушка не найдена в папке static!")
        print("ℹ️ Будет использоваться режим без изображений")
    
    # Запускаем HTTP сервер для здоровья
    health_runner = await health_server()
    
    try:
        # Запускаем ВСЕ задачи
        tasks = [
            asyncio.create_task(bot.polling(non_stop=True)),
            asyncio.create_task(auto_poster()),
            asyncio.create_task(enhanced_keep_alive())
        ]
        
        print("✅ Все задачи запущены")
        await asyncio.gather(*tasks)
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
    finally:
        await health_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен")
        save_posted_news(posted_news)
    except Exception as e:
        print(f"💥 Фатальная ошибка: {e}")
        save_posted_news(posted_news)


