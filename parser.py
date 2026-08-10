from curl_cffi.requests import AsyncSession
import asyncio
from bs4 import BeautifulSoup
from aiogram import Bot
from database.requests import get_active_sniper_filters, update_sniper_last_id, save_found_item
from database.models import FoundItem
from database.db import async_session

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.olx.ua/',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1'
}

# --- НОВАЯ ФУНКЦИЯ: Проверка найденного лота по фильтрам пользователя ---
def matches_filter(item: dict, item_filter) -> bool:
    # 1. Проверка цены
    if item_filter.price:
        # Вытаскиваем только цифры из "1 500 грн." -> 1500
        digits = ''.join(filter(str.isdigit, item['price']))
        if digits:
            item_price = int(digits)
            if item_price > item_filter.price:
                return False

    # 2. Проверка бренда (ищем в названии)
    title_lower = item['title'].lower()
    if item_filter.brand and item_filter.brand.lower() not in title_lower:
        return False

    # 3. Проверка размера (ищем в названии)
    if item_filter.size and item_filter.size.lower() not in title_lower:
        return False
        
    # Состояние (condition) с общей страницы поиска парсить сложно без захода в само объявление,
    # поэтому мы пока опираемся на цену, бренд и размер.
    
    return True
# ------------------------------------------------------------------------

async def fetch_olx_items(url: str):
    async with AsyncSession(impersonate="chrome120") as session:
        response = await session.get(url, headers=HEADERS)
        print("Статус ответа от OLX:", response.status_code)

        html_text = response.text
        soup = BeautifulSoup(html_text, 'html.parser') 

        page_title = soup.title.text if soup.title else "Без заголовка"
        print("Заголовок страницы:", page_title)

        cards = soup.find_all('div', {'data-cy': 'l-card'})

        if not cards:
            print("Товары не найдены")
            return None

        card = cards[0]

        link_element = card.find('a')
        href = link_element['href']
        link = href if href.startswith("http") else f"https://www.olx.ua{href}"
            
        title = card.find('h4').text.strip()

        price_element = card.find('p', {'data-testid': 'ad-price'})
        price = price_element.text.strip() if price_element else "Цена не указана"

        img_elemnt = card.find('img')
        photo = img_elemnt['src'] if img_elemnt else None

        item_id = card.get('id') or link_element['href'].split('-ID')[-1].replace('.html', '')

        return {
            'id': item_id,
            'title': title,
            'price': price,
            'url': link,
            'photo': photo
        }


async def start_sniper_worker(bot: Bot):
    print("🚀 Снайпер-воркер запущен!")
    while(True):
        try:
            filters = await get_active_sniper_filters()
            print(f"📊 Найдено активных фильтров в базе: {len(filters)}")

            for item_filter in filters:
                print(f"🎯 [ВОРКЕР ПАРСИТ]: ID={item_filter.id} | URL={item_filter.url}")
                item = await fetch_olx_items(item_filter.url)

                if not item:
                    print("⚠️ Не удалось распарсить товары по этой ссылке")
                    continue

                if item_filter.last_item_id is None:
                    print(f"⚙️ Первая проверка для фильтра {item_filter.id}. Запоминаем текущий последний лот: {item['id']}")
                    await update_sniper_last_id(item_filter.id, item['id'])

                elif item['id'] != item_filter.last_item_id:
                    print(f"🔥 НАЙДЕН НОВЫЙ ТОВАР! ID: {item['id']} (старый: {item_filter.last_item_id})")

                    # --- ИСПОЛЬЗУЕМ ФИЛЬТР ---
                    if not matches_filter(item, item_filter):
                        print("⛔️ Товар не прошел по фильтрам (цена/бренд/размер). Пропускаем.")
                        # Обязательно обновляем ID, чтобы воркер не зациклился на этом товаре!
                        await update_sniper_last_id(item_filter.id, item['id'])
                        continue
                    # -------------------------

                    # Если товар подошел, сохраняем в БД (исправлены отступы!)
                    await save_found_item(
                        user_id=item_filter.user_id,
                        title=item['title'],
                        price=item['price'],
                        url=item['url'],
                        photo=item.get('photo')
                    )

                    # Обновляем ID (исправлены отступы!)
                    await update_sniper_last_id(item_filter.id, item['id'])

                    # Отправляем уведомление (исправлены отступы!)
                    try:
                        await bot.send_message(
                            chat_id=item_filter.user_id,
                            text="🔔 <b>Снайпер нашёл новую подходящую вещь!</b>\nПерейдите в <i>«📦 Найденные лоты»</i>, чтобы посмотреть.",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Ошибка отправки пользователю {item_filter.user_id}: {e}")

            await asyncio.sleep(5)

        except Exception as e:
            print(f"Ошибка в главном цикле воркера: {e}")
            pass
        
        print("💤 Воркер уходит в сон на 3 минуты...")
        await asyncio.sleep(180)


if __name__ == "__main__":
    test_url = "https://www.olx.ua/uk/list/q-rick-owens/"
    result = asyncio.run(fetch_olx_items(test_url))
    print("Результат парсинга:", result)