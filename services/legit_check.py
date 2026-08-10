import re

def check_item_code(raw_code: str) -> dict:
    code = raw_code.strip().upper()

    # 1. Проверка на CLG-код (12 цифр)
    clean_clg = re.sub(r'\D', '', code)
    if len(clean_clg) == 12:
        return {
            "type": "clg",
            "code": clean_clg,  # Передаем чистый 12-значный код без пробелов
            "url": "https://www.certilogo.com/code",
            "message": (
                f"🛡 **Обнаружен CLG-код:** `{clean_clg}`\n\n"
                f"1. Нажмите на код выше, чтобы скопировать его.\n"
                f"2. Перейдите по кнопке ниже и вставьте код в поле."
            )
        }

    # 2. Проверка на Nike Style Code (Формат: CW2288-111 или CW2288111)
    nike_pattern = r'^[A-Z0-9]{6}-?\d{3}$'
    if re.match(nike_pattern, code):
        if '-' not in code:
            formatted_nike = f"{code[:6]}-{code[6:]}"
        else:
            formatted_nike = code

        google_search_url = f"https://www.google.com/search?q=Nike+{formatted_nike}"
        stockx_url = f"https://stockx.com/search?s={formatted_nike}"

        return {
            "type": "nike",
            "code": formatted_nike,
            "google_url": google_search_url,
            "stockx_url": stockx_url,
            "message": (
                f"👟 **Обнаружен артикул Nike/Jordan:** `{formatted_nike}`\n\n"
                f"Артикул соответствует формату производителя. Сверьте название и расцветку модели на бирке с данными по ссылкам ниже:"
            )
        }

    # 3. Неизвестный формат
    return {
        "type": "unknown",
        "message": (
            "❌ **Неверный формат кода.**\n\n"
            "• Для **Certilogo** введите 12 цифр (например, `123 456 789 012`)\n"
            "• Для **Nike/Jordan** введите артикул (например, `CW2288-111`)"
        )
    }