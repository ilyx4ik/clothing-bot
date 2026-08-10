import re
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as DbSession
from sqlalchemy import select, or_
from database.models import Item


# 1. Поиск по внутренней базе бота
async def get_internal_stats(session: DbSession, query_text: str) -> dict | None:
    words = query_text.strip().split()
    if not words:
        return None

    conditions = [Item.title.ilike(f"%{word}%") for word in words if len(word) > 1]
    if not conditions:
        return None

    stmt = select(Item.price).where(or_(*conditions))
    result = await session.execute(stmt)
    prices = result.scalars().all()

    if not prices:
        return None

    return {
        "count": len(prices),
        "min": min(prices),
        "max": max(prices),
        "avg": int(sum(prices) / len(prices))
    }


# 2. Прямой парсер OLX.ua с имитацией TLS Chrome (без 403)
async def get_olx_stats(query_text: str) -> dict | None:
    encoded_query = query_text.strip().replace(" ", "-")
    url = f"https://www.olx.ua/d/uk/list/q-{encoded_query}/"

    try:
        # impersonate="chrome120" полностью подделывает отпечаток Chrome
        async with AsyncSession() as session:
            response = await session.get(url, impersonate="chrome120", timeout=8)
            print(f"[OLX Parser] Status Code: {response.status_code}")
            
            if response.status_code != 200:
                return None
            
            html = response.text

        soup = BeautifulSoup(html, "html.parser")
        prices = []

        # Поиск 1: По элементам цен OLX
        elements = soup.find_all(attrs={"data-testid": "ad-price"})
        for elem in elements:
            raw_text = elem.get_text()
            clean_price = re.sub(r'\D', '', raw_text)
            if clean_price and 100 <= int(clean_price) <= 300000:
                prices.append(int(clean_price))

        # Поиск 2 (Резервный): Регулярка по всему HTML, если верстка изменилась
        if not prices:
            found = re.findall(r'(\d[\d\s]{1,6})\s*(?:грн|₴|UAH)', html, re.IGNORECASE)
            for p in found:
                clean_p = re.sub(r'\D', '', p)
                if clean_p and 100 <= int(clean_p) <= 300000:
                    prices.append(int(clean_p))

        if not prices:
            print("[OLX Parser] Цены на странице не найдены")
            return None

        # Берем первые 20 релевантных цен
        prices = prices[:20]

        return {
            "count": len(prices),
            "min": min(prices),
            "max": max(prices),
            "avg": int(sum(prices) / len(prices))
        }

    except Exception as e:
        print(f"[OLX Parser Error]: {e}")
        return None


# 3. Главный гибридный оценщик
async def get_full_evaluation(session: DbSession, query_text: str) -> dict:
    internal = await get_internal_stats(session, query_text)
    olx = await get_olx_stats(query_text)

    if not internal and not olx:
        return {"status": "not_found"}

    all_prices = []
    if internal:
        all_prices.append(internal["avg"])
    if olx:
        all_prices.append(olx["avg"])

    recommended_price = int(sum(all_prices) / len(all_prices))

    return {
        "status": "ok",
        "query": query_text,
        "internal": internal,
        "olx": olx,
        "recommended_price": recommended_price,
        "fast_sale_price": int(recommended_price * 0.85)
    }