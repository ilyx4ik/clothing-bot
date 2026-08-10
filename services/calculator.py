import aiohttp

# Запасные курсы на случай, если API ПриватБанка будет недоступно
FALLBACK_RATES = {
    "USD": 41.5,
    "EUR": 45.0,
    "PLN": 10.5,
    "CNY": 5.8
}

DELIVERY_RATE_PER_KG = 415.0    

async def get_exchange_rate(currency: str = "USD") -> float:
    """
    Получает актуальный курс валюты к UAH через публичный API ПриватБанка.
    """
    url = "https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    for item in data:
                        if item.get("ccy") == currency.upper():
                            return float(item.get("sale"))
        except Exception as e:
            print(f"Ошибка получения курса валют: {e}")
            
    return None


async def calculate_total(price: float, currency: str, weight_kg: float = 0.5) -> dict:
    currency_code = currency.upper()
    
    # Получаем актуальный курс через API
    rate = await get_exchange_rate(currency_code)
    
    # Если API недоступно, используем статический фоллбэк
    if not rate:
        rate = FALLBACK_RATES.get(currency_code, 41.5)
    
    # 1. Считаем стоимость товара в UAH
    item_cost_uah = price * rate
    
    # 2. Считаем стоимость доставки в UAH
    shipping_cost_uah = weight_kg * DELIVERY_RATE_PER_KG
    
    # 3. Итоговая сумма
    total_uah = item_cost_uah + shipping_cost_uah
    
    return {
        "currency": currency_code,
        "rate": rate,
        "price_orig": price,
        "item_cost_uah": round(item_cost_uah, 2),
        "shipping_cost_uah": round(shipping_cost_uah, 2),
        "total_uah": round(total_uah, 2)
    }