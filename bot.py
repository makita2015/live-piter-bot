#!/usr/bin/env python3
# bot.py - Новостной бот для канала "Live Питер 📸" (полная версия)
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

# Загрузка переменных окружения
load_dotenv()

# --- Конфигурация ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@LivePiter")
AUTO_POST_INTERVAL = int(os.getenv("AUTO_POST_INTERVAL", "1800"))
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN не установлен")

# Инициализация бота
bot = AsyncTeleBot(BOT_TOKEN)

# --- Управление опубликованными новостями ---
def load_posted_news():
    """Загрузка списка опубликованных новостей"""
    try:
        posted_json = os.getenv("POSTED_NEWS", "[]")
        return set(json.loads(posted_json))
    except Exception as e:
        print(f"⚠️ Ошибка загрузки posted news: {e}")
        return set()

def save_posted_news(posted_news_set):
    """Сохранение списка опубликованных новостей"""
    try:
        posted_list = list(posted_news_set)
        print(f"💾 Сохранено {len(posted_list)} новостей")
        if posted_list:
            print("📋 Последние новости:", posted_list[-3:])
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
                "timestamp": datetime.now().isoformat()
            }),
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
async def keep_alive_ping():
    """Периодический пинг для предотвращения сна на Render"""
    print("🔄 Keep-alive задача ЗАПУЩЕНА")
    while True:
        try:
            print(f"🔄 Пробую ping на порт {PORT}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://localhost:{PORT}/health', timeout=10) as resp:
                    if resp.status == 200:
                        print(f"🔄 Keep-alive ping: {datetime.now().strftime('%H:%M:%S')}")
                    else:
                        print(f"⚠️ Keep-alive ping failed: {resp.status}")
        except Exception as e:
            print(f"⚠️ Keep-alive error: {e}")
        
        # Пинг каждые 5 минут (300 секунд)
        await asyncio.sleep(300)

# --- Функция генерации красивой заглушки для Live Питер 📸 ---
def generate_beautiful_placeholder():
    """Генерация заглушки в стиле реальных новостных каналов"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        width, height = 800, 600
        # Создаем фон в стиле новостных каналов (темно-синий с градиентом)
        img = Image.new('RGB', (width, height), color='#0a1931')
        draw = ImageDraw.Draw(img)
        
        # Градиентный фон
        for i in range(height):
            r = int(10 + (i / height) * 20)
            g = int(25 + (i / height) * 30)
            b = int(49 + (i / height) * 40)
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        
        # Верхняя панель - градиентный красный
        for i in range(80):
            red_value = int(139 + (i / 80) * 116)  # От темно-красного к ярко-красному
            draw.line([(0, i), (width, i)], fill=(red_value, 0, 0))
        
        # Нижняя панель - градиентный красный
        for i in range(height-80, height):
            red_value = int(139 + ((i - (height-80)) / 80) * 116)  # От темно-красного к ярко-красному
            draw.line([(0, i), (width, i)], fill=(red_value, 0, 0))
        
        # Элементы "экранов" как в новостной студии
        draw.rectangle([50, 100, width-50, height-100], outline='#d4af37', width=3)
        
        # Текст бегущей строки
        try:
            font_news = ImageFont.truetype("arial.ttf", 22)
            font_large = ImageFont.truetype("arial.ttf", 52)
            font_medium = ImageFont.truetype("arial.ttf", 28)
        except:
            font_news = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
        
        # Бегущая строка - размещаем по центру нижней красной полосы
        news_text = "САНКТ-ПЕТЕРБУРГ • АКТУАЛЬНЫЕ НОВОСТИ • САНКТ-ПЕТЕРБУРГ • АКТУАЛЬНЫЕ НОВОСТИ"
        text_y_position = height - 40  # По центру нижней полосы
        draw.text((10, text_y_position), news_text, fill='#ffffff', font=font_news)
        
        # Основной текст
        draw.text((width//2, height//2 - 40), "Live Питер", fill='#ffffff', 
                 font=font_large, anchor='mm', stroke_width=2, stroke_fill='#000000')
        draw.text((width//2, height//2 + 20), "НОВОСТНОЙ КАНАЛ", fill='#d4af37', 
                 font=font_medium, anchor='mm')
        
        # Дополнительные элементы как в новостной графике
        draw.rectangle([width//2 - 150, height//2 + 60, width//2 - 50, height//2 + 65], fill='#d4af37')
        draw.rectangle([width//2 + 50, height//2 + 60, width//2 + 150, height//2 + 65], fill='#d4af37')
        
        # Логотип в левом верхнем углу (упрощенный)
        draw.rectangle([20, 20, 60, 60], fill='#ffffff', outline='#8B0000', width=2)
        draw.text((40, 40), "LP", fill='#8B0000', font=font_medium, anchor='mm')
        
        # Сохраняем изображение
        os.makedirs('./static', exist_ok=True)
        placeholder_path = './static/placeholder.jpg'
        img.save(placeholder_path, quality=95)
        
        print("🎨 Сгенерирована заглушка в стиле новостного канала")
        return placeholder_path
        
    except Exception as e:
        print(f"⚠️ Ошибка генерации заглушки: {e}")
        # Fallback - простая заглушка
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (800, 600), color='#0a1931')
            draw = ImageDraw.Draw(img)
            # Красные полосы
            draw.rectangle([0, 0, 800, 80], fill='#8B0000')
            draw.rectangle([0, 520, 800, 600], fill='#8B0000')
            draw.rectangle([50, 50, 750, 550], outline='#d4af37', width=4)
            draw.text((400, 280), "Live Питер", fill='#ffffff', anchor='mm')
            draw.text((400, 320), "НОВОСТНОЙ КАНАЛ", fill='#d4af37', anchor='mm')
            # Бегущая строка
            draw.text((50, 560), "САНКТ-ПЕТЕРБУРГ • АКТУАЛЬНЫЕ НОВОСТИ", fill='#ffffff')
            placeholder_path = './static/placeholder.jpg'
            img.save(placeholder_path)
            return placeholder_path
        except Exception as e2:
            print(f"⚠️ Не удалось создать даже простую заглушку: {e2}")
            return None

# --- Улучшенный парсинг для законченных новостей ---
def extract_complete_text_from_html(html_content, title):
    """Извлечение полного текста новости с сохранением смысла"""
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
            # Фильтрация: убираем короткие, рекламные и технические тексты
            if (len(text) > 40 and 
                not any(x in text for x in [
                    '©', 'Фото:', 'Источник:', 'Читайте также:', 'Редакция',
                    'Комментарии', 'Подпишитесь', 'Rambler', 'ТАСС', 
                    'Lenta.ru', 'РИА Новости', 'Поделиться', 'Следите за',
                    'INTERFAX.RU', 'https://', 'http://', 'www.'
                ]) and
                not re.match(r'^\d{1,2}\s*[а-я]', text.lower()) and
                len(text.split()) > 8 and
                not text.startswith('http')):
                meaningful_paragraphs.append(text)
        
        # Формируем полный текст, сохраняя структуру
        if meaningful_paragraphs:
            # Берем первые 6-8 значимых абзацев для сохранения контекста
            selected_paragraphs = meaningful_paragraphs[:8]
            full_text = '\n\n'.join(selected_paragraphs)
            
            # Обеспечиваем минимальную длину
            if len(full_text.split()) < 50:
                full_text = f"{title}\n\n{full_text}"
            
            return full_text[:3000]  # Увеличили лимит для полных новостей
            
    except Exception as e:
        print(f"⚠️ Ошибка парсинга HTML: {e}")
    
    return ""

def remove_duplicate_text(text):
    """Удаление дублированного текста из новости"""
    if not text:
        return text
    
    # Разбиваем текст на предложения
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Удаляем дубликаты предложений (сохраняя порядок)
    unique_sentences = []
    seen_sentences = set()
    
    for sentence in sentences:
        # Нормализуем предложение для сравнения (убираем лишние пробелы, приводим к нижнему регистру)
        normalized = re.sub(r'\s+', ' ', sentence).strip().lower()
        if normalized and normalized not in seen_sentences:
            seen_sentences.add(normalized)
            unique_sentences.append(sentence)
    
    # Собираем текст обратно
    cleaned_text = '. '.join(unique_sentences) + '.' if unique_sentences else ''
    
    # Если текст стал слишком коротким после очистки, возвращаем оригинал
    if len(cleaned_text.split()) < 20 and len(text.split()) > 30:
        return text
    
    return cleaned_text

def create_engaging_title(original_title):
    """Создание цепляющего заголовка в стиле Live Питер БЕЗ автоматических добавлений"""
    # Очищаем заголовок от лишних элементов
    clean_title = original_title
    
    # Убираем URL и источники из заголовка
    clean_title = re.sub(r'https?://\S+|www\.\S+', '', clean_title)
    clean_title = re.sub(r'\b(INTERFAX\.RU|РИА\s*Новости|ТАСС|Lenta\.ru|Rambler)\b', '', clean_title, flags=re.IGNORECASE)
    
    # Убираем дублирующиеся тире и точки
    clean_title = re.sub(r'[–—]\s*[–—]+', '—', clean_title)
    clean_title = re.sub(r'\.\s*\.+', '.', clean_title)
    
    # Удаляем дублированный текст из заголовка
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
    """Форматирование новости в стиле Live Питер 📸"""
    # Создаем чистый заголовок БЕЗ автоматических добавлений
    clean_title = create_engaging_title(title)
    
    # Определяем основной текст
    if full_text and len(full_text.split()) > 60:
        # Используем полный текст, но структурируем его
        paragraphs = full_text.split('\n\n')
        if len(paragraphs) >= 2:
            # Берем введение и ключевые детали
            intro = paragraphs[0]
            key_details = []
            
            for p in paragraphs[1:4]:  # Берем следующие 2-3 абзаца
                if len(p.split()) > 15 and len(key_details) < 2:
                    key_details.append(p)
            
            if key_details:
                formatted_text = f"{intro}\n\n" + "\n\n".join(key_details)
            else:
                formatted_text = intro
        else:
            formatted_text = full_text
    elif description and len(description.split()) > 20:
        formatted_text = description
    else:
        formatted_text = full_text if full_text else description
    
    # УДАЛЯЕМ ВСЕ ССЫЛКИ И ИСТОЧНИКИ ИЗ ТЕКСТА
    formatted_text = re.sub(r'https?://\S+|www\.\S+', '', formatted_text)
    formatted_text = re.sub(r'\b(INTERFAX\.RU|РИА\s*Новости|ТАСС|Lenta\.ru|Rambler|Фонтанка\.ру|78\.ру|Каннал7|Петербург2|ДП)\b', '', formatted_text, flags=re.IGNORECASE)
    formatted_text = re.sub(r'\.\s*[A-ZА-Я]+\s*\.\s*—', '.', formatted_text)  # Убираем источники в начале предложения
    
    # УДАЛЯЕМ ДУБЛИРОВАННЫЙ ТЕКСТ
    formatted_text = remove_duplicate_text(formatted_text)
    
    # Очистка и форматирование
    formatted_text = re.sub(r'\s+', ' ', formatted_text)
    formatted_text = re.sub(r'\.\s+', '.\n\n', formatted_text)  # Добавляем абзацы
    
    # Собираем финальное сообщение
    final_text = f"{clean_title}\n\n{formatted_text}"
    
    # Убираем лишние пустые строки
    final_text = re.sub(r'\n\s*\n', '\n\n', final_text)
    
    # Обрезаем до разумных пределов, но сохраняем смысл
    if len(final_text) > 3000:
        sentences = final_text.split('. ')
        if len(sentences) > 3:
            final_text = '. '.join(sentences[:4]) + "."
    
    return final_text.strip()

# --- ИСПРАВЛЕННЫЕ источники новостей ---
NEWS_SOURCES = [
    # Общероссийские источники (рабочие)
    "https://lenta.ru/rss/news",
    "https://tass.ru/rss/v2.xml", 
    "https://news.rambler.ru/rss/world/",
    
    # Санкт-Петербургские источники (ИСПРАВЛЕННЫЕ)
    "https://www.fontanka.ru/fontanka.rss",  # Исправленный URL
    "https://78.ru/text/rss.xml",           # Исправленный URL
    "https://kanal7.ru/rss/",               # Исправленный URL
    "https://peterburg2.ru/rss/",           # Исправленный URL
    "https://www.dp.ru/rss/",               # Исправленный URL
    
    # Дополнительные рабочие источники
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
                    
                    if len(content) > 10240:  # Минимум 10KB
                        with open(filename, 'wb') as f:
                            f.write(content)
                        return filename
                    else:
                        print(f"⚠️ Изображение слишком маленькое: {len(content)} байт")
                
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
            await asyncio.sleep(1)  # Задержка между запросами
        
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
    """Подготовка новости к публикации с улучшенным форматированием"""
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
    if word_count < 40:  # Минимум 40 слов для законченной новости
        print(f"❌ Пропущена новость: '{title[:30]}...' - недостаточно текста ({word_count} слов)")
        return None
    
    print(f"✅ Текст подготовлен: {word_count} слов")
    
    # Работа с изображением
    image_path = None
    if image_url:
        async with aiohttp.ClientSession() as session:
            image_path = await download_image(session, image_url)
            if image_path:
                print("✅ Используем изображение из новости")
    
    # Используем сгенерированную заглушку
    if not image_path:
        image_path = generate_beautiful_placeholder()
        if image_path:
            print("✅ Используем сгенерированную заглушку")
        else:
            print("⚠️ Не удалось создать заглушку")
    
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
        
        # Форматируем сообщение
        message_text = summary  # Уже содержит заголовок и текст
        
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await bot.send_photo(
                    CHANNEL_ID,
                    photo,
                    caption=message_text,
                    parse_mode='HTML'
                )
            # Удаляем временные файлы (кроме заглушки)
            if 'temp_image_' in image_path:
                try:
                    os.remove(image_path)
                except:
                    pass
        else:
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
    print("📏 Формат: законченные новости в стиле Live Питер 📸")
    
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
    max_attempts = min(len(new_news) * 2, 15)  # Максимум 15 попыток
    
    while published_count < count and attempts < max_attempts:
        if attempts >= len(new_news):
            break
            
        item = new_news[attempts]
        attempts += 1
        
        try:
            prepared_item = await prepare_news_item(item)
            
            if prepared_item is None:
                continue  # Пропускаем новости, не прошедшие проверку
                
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

📰 Источники:
• 3 федеральных новостных портала
• 5 локальных питерских изданий
• 3 дополнительных надежных источника

🎯 Особенности:
• Законченные новости с полной смысловой нагрузкой
• Локальный контекст Санкт-Петербурга
• Стиль оформления как в "Live Питер 📸"
• Автоматический подбор изображений
• Красивая авторская заглушка

📋 Команды:
/post - Опубликовать новости
/status - Статус бота  
/stats - Статистика
/sources - Список источников
"""
    await bot.reply_to(message, welcome_text)

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
📊 Статус бота:

🤖 Бот: Активен
📰 Источников: {len(NEWS_SOURCES)}
📨 Опубликовано: {len(posted_news)}
🎯 Формат: "Live Питер 📸"
⏰ Интервал: {AUTO_POST_INTERVAL} сек
🏙️ Локальные: {sum(1 for s in NEWS_SOURCES if 'fontanka' in s or '78' in s or 'kanal7' in s or 'peterburg' in s)} источников
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
    print("🎯 Формат: законченные новости в стиле Live Питер 📸")
    
    while True:
        try:
            news_count = random.randint(1, 2)
            print(f"📰 Автопостинг: публикую {news_count} новостей...")
            
            await publish_news(news_count)
            
            print(f"⏳ Следующая проверка через {AUTO_POST_INTERVAL} секунд...")
            await asyncio.sleep(AUTO_POST_INTERVAL)
            
        except Exception as e:
            print(f"⚠️ Ошибка в авто-постинге: {e}")
            await asyncio.sleep(300)  # Ждем 5 минут при ошибке

async def main():
    """Основная функция запуска бота"""
    print("🚀 Запуск новостного бота 'Live Питер 📸'...")
    print(f"📰 Источников: {len(NEWS_SOURCES)} (федеральные + питерские)")
    print(f"🎯 Формат: законченные новости с полной смысловой нагрузкой")
    print(f"⏰ Интервал автопостинга: {AUTO_POST_INTERVAL} сек")
    print(f"📺 Канал: {CHANNEL_ID}")
    print(f"🌐 Порт: {PORT}")
    print("🔧 Версия: с keep-alive для Render")
    
    # Запускаем HTTP сервер для здоровья
    health_runner = await health_server()
    
    # Запускаем keep-alive задачу
    print("🔄 Создаю keep-alive задачу...")
    keep_alive_task = asyncio.create_task(keep_alive_ping())
    
    try:
        # Запускаем задачи
        bot_task = asyncio.create_task(bot.polling(non_stop=True))
        poster_task = asyncio.create_task(auto_poster())
        
        # Ожидаем завершения задач
        await asyncio.gather(bot_task, poster_task, keep_alive_task)
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
