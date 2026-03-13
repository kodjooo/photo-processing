from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

try:
    import rawpy
except ImportError:  # pragma: no cover
    rawpy = None

from app.enums import ProcessingPreset


@dataclass(slots=True)
class ImageMetrics:
    brightness: float
    contrast: float
    sharpness: float
    dark_ratio: float
    bright_ratio: float


class ImageProcessor:
    def load_logo(self, logo_path: str, base_width: int, base_height: int) -> Image.Image:
        path = Path(logo_path)
        if not path.exists():
            return Image.new("RGBA", (1, 1), (255, 255, 255, 0))
        logo = Image.open(path).convert("RGBA")
        target_width = max(80, int(base_width * 0.12))
        ratio = target_width / max(1, logo.width)
        target_height = max(1, int(logo.height * ratio))
        return logo.resize((target_width, target_height))

    def process_image(
        self,
        source_path: Path,
        target_path: Path,
        *,
        preset: ProcessingPreset,
        left_logo_path: str,
        right_logo_path: str,
    ) -> None:
        image = self.load_source_image(source_path)
        metrics = self.calculate_metrics(image)
        processed = self.apply_pipeline(image, metrics, preset)
        composed = self.apply_logos(processed, left_logo_path, right_logo_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        composed.save(target_path, quality=95)

    def load_source_image(self, source_path: Path) -> Image.Image:
        if source_path.suffix.lower() in {".cr2", ".arw"}:
            if rawpy is None:
                raise RuntimeError("Поддержка RAW недоступна: не установлена библиотека rawpy")
            with rawpy.imread(str(source_path)) as raw:
                rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=False, output_bps=8)
            return Image.fromarray(rgb).convert("RGB")

        image = Image.open(source_path)
        return ImageOps.exif_transpose(image).convert("RGB")

    def calculate_metrics(self, image: Image.Image) -> ImageMetrics:
        grayscale = image.convert("L")
        stat = ImageStat.Stat(grayscale)
        brightness = stat.mean[0] / 255
        contrast = stat.stddev[0] / 255
        edges = grayscale.filter(ImageFilter.FIND_EDGES)
        sharpness = ImageStat.Stat(edges).mean[0] / 255
        histogram = grayscale.histogram()
        total_pixels = max(1, sum(histogram))
        dark_ratio = sum(histogram[:30]) / total_pixels
        bright_ratio = sum(histogram[225:]) / total_pixels
        return ImageMetrics(
            brightness=brightness,
            contrast=contrast,
            sharpness=sharpness,
            dark_ratio=dark_ratio,
            bright_ratio=bright_ratio,
        )

    def apply_pipeline(
        self,
        image: Image.Image,
        metrics: ImageMetrics,
        preset: ProcessingPreset,
    ) -> Image.Image:
        brightness_factor = 1.0
        contrast_factor = 1.0
        color_factor = 1.03
        sharpness_factor = 1.02

        if metrics.brightness < 0.42:
            brightness_factor += 0.08
        if metrics.bright_ratio > 0.18:
            brightness_factor -= 0.03
        if metrics.contrast < 0.20:
            contrast_factor += 0.10
        if metrics.sharpness < 0.08:
            sharpness_factor += 0.08

        if preset == ProcessingPreset.SOFT:
            contrast_factor -= 0.04
            color_factor -= 0.01
        if preset == ProcessingPreset.CONTRAST:
            contrast_factor += 0.10
            sharpness_factor += 0.05

        processed = ImageEnhance.Brightness(image).enhance(brightness_factor)
        processed = ImageEnhance.Contrast(processed).enhance(contrast_factor)
        processed = processed.filter(ImageFilter.MedianFilter(size=3))
        processed = ImageEnhance.Color(processed).enhance(color_factor)
        processed = ImageEnhance.Sharpness(processed).enhance(sharpness_factor)
        return processed

    def apply_logos(self, image: Image.Image, left_logo_path: str, right_logo_path: str) -> Image.Image:
        canvas = image.convert("RGBA")
        left_logo = self._set_opacity(self.load_logo(left_logo_path, canvas.width, canvas.height), 0.35)
        right_logo = self._set_opacity(self.load_logo(right_logo_path, canvas.width, canvas.height), 0.35)
        padding = max(16, int(canvas.width * 0.02))
        canvas.alpha_composite(left_logo, (padding, max(0, canvas.height - left_logo.height - padding)))
        canvas.alpha_composite(
            right_logo,
            (max(0, canvas.width - right_logo.width - padding), max(0, canvas.height - right_logo.height - padding)),
        )
        return canvas.convert("RGB")

    def _set_opacity(self, image: Image.Image, opacity: float) -> Image.Image:
        alpha = image.getchannel("A")
        adjusted = alpha.point(lambda value: int(value * opacity))
        return Image.merge("RGBA", (*image.convert("RGB").split(), adjusted))
