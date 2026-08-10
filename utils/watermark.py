import io
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot
from aiogram.types import BufferedInputFile

async def add_watermark_on_photo(
        bot: Bot,
        file_id: str,
        watermark_text: str = "@plugstudio_store_bot"
) -> BufferedInputFile:

    file_info = await bot.get_file(file_id)
    photo_bytes = await bot.download_file(file_info.file_path)

    base_image = Image.open(photo_bytes).convert("RGBA")

    txt_layer = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    width, height = base_image.size
    font_size = max(24, int(width * 0.05))

    # Кроссплатформенный подбор шрифта
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except (IOError, OSError):
            try:
                font = ImageFont.load_default(size=font_size)
            except TypeError:
                font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Отступы от правого нижнего угла
    margin = int(width * 0.03)
    x = width - text_width - margin
    y = height - text_height - margin

    # Тень (черная)
    draw.text((x + 2, y + 2), watermark_text, font=font, fill=(0, 0, 0, 180))
    # Основной текст (белый)
    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 220))

    watermarked = Image.alpha_composite(base_image, txt_layer)

    output_stream = io.BytesIO()
    watermarked.convert("RGB").save(output_stream, format="JPEG", quality=90)
    output_bytes = output_stream.getvalue()

    return BufferedInputFile(output_bytes, filename="watermarked_photo.jpg")