"""Gera assets/pluseduc.ico (círculo azul do logo da interface com a letra P). Rode só para trocar o visual."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "assets" / "pluseduc.ico"
SIZE = 512


def draw() -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas = ImageDraw.Draw(image)
    canvas.ellipse((16, 16, SIZE - 16, SIZE - 16), fill="#4FC3F7")      # anel claro
    canvas.ellipse((48, 48, SIZE - 48, SIZE - 48), fill="#1E5AA8")      # círculo do logo
    font = next((ImageFont.truetype(name, 300) for name in ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf") if _has(name)), ImageFont.load_default(300))
    canvas.text((SIZE / 2, SIZE / 2 + 8), "P", font=font, fill="white", anchor="mm")
    return image


def _has(name: str) -> bool:
    try:
        ImageFont.truetype(name, 10)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    draw().save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Ícone gerado em {OUT}")
