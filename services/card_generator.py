from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


async def generate_item_card(image_bytes: bytes, title: str, price: str, size: str, brand: str):
    width = 800
    height = 1000

    background_color = 'black'

    canvas = Image.new('RGB', (width, height), color=background_color)

    item_photo = Image.open(BytesIO(image_bytes))

    item_photo = item_photo.resize((600, 500))

    canvas.paste(item_photo, (100, 50))

    draw = ImageDraw.Draw(canvas)
    font_title = ImageFont.truetype("arial.ttf", size=36)

    draw.text((100, 640), text=f"Бренд: {brand}", font=font_title, fill="white")
    draw.text((100, 580), text=title, font=font_title, fill="white")
    draw.text((100, 690), text=f"Размер: {size}", font=font_title, fill="white")
    draw.text((100, 750), text=f"Цена: {int(float(price))} UAH", font=font_title, fill="yellow")

    output = BytesIO()

    canvas.save(output, format="PNG")

    output.seek(0)

    return output