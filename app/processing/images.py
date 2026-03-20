from dataclasses import dataclass
from pathlib import Path

import numpy as np

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

try:
    import rawpy
except ImportError:  # pragma: no cover
    rawpy = None

from app.config import get_settings
from app.enums import ProcessingPreset


@dataclass(slots=True)
class ImageMetrics:
    brightness: float
    contrast: float
    sharpness: float
    dark_ratio: float
    bright_ratio: float


class ImageProcessor:
    def __init__(self) -> None:
        self.settings = get_settings()

    def load_logo(self, logo_path: str, base_width: int, base_height: int) -> Image.Image:
        path = Path(logo_path)
        if not path.exists():
            return Image.new("RGBA", (1, 1), (255, 255, 255, 0))
        logo = Image.open(path).convert("RGBA")
        width_ratio = 0.15 if base_width > base_height else 0.25
        target_width = max(80, int(base_width * width_ratio))
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

    def export_decoded_image(
        self,
        source_path: Path,
        target_path: Path,
        *,
        raw_auto_bright: bool,
    ) -> None:
        image = self.load_source_image(source_path, raw_auto_bright=raw_auto_bright)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(target_path, quality=95)

    def load_source_image(self, source_path: Path, *, raw_auto_bright: bool = True) -> Image.Image:
        if source_path.suffix.lower() in {".cr2", ".arw"}:
            return self._load_raw_image(source_path, auto_bright=raw_auto_bright)

        image = Image.open(source_path)
        return ImageOps.exif_transpose(image).convert("RGB")

    def _load_raw_image(self, source_path: Path, *, auto_bright: bool) -> Image.Image:
        if rawpy is None:
            raise RuntimeError("Поддержка RAW недоступна: не установлена библиотека rawpy")
        with rawpy.imread(str(source_path)) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=not auto_bright,
                output_bps=8,
            )
        return Image.fromarray(rgb).convert("RGB")

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
        preset = self._normalize_preset(preset)
        if self._is_global_preset(preset):
            return self._apply_global_pipeline(image, metrics, preset)
        return self._apply_local_pipeline(image, metrics, preset)

    def _apply_local_pipeline(
        self,
        image: Image.Image,
        metrics: ImageMetrics,
        preset: ProcessingPreset,
    ) -> Image.Image:
        preset = self._normalize_preset(preset)

        brightness_factor = 1.0
        contrast_factor = 1.0
        color_factor = 1.01
        sharpness_factor = 1.0
        shadow_lift = 0.05
        highlight_recovery = 0.04
        local_contrast_strength = 0.03
        vibrance_strength = 0.02

        if metrics.brightness < 0.42:
            brightness_factor += 0.04
            shadow_lift += 0.03
        if metrics.bright_ratio > 0.18:
            brightness_factor -= 0.02
            highlight_recovery += 0.03
        if metrics.contrast < 0.20:
            contrast_factor += 0.05
            local_contrast_strength += 0.03
        if metrics.sharpness < 0.08:
            sharpness_factor += 0.03

        if preset == ProcessingPreset.NATURAL:
            brightness_factor -= 0.005 if metrics.bright_ratio > 0.12 else 0.0
            contrast_factor -= 0.01
            color_factor = 1.0
            sharpness_factor = max(0.98, sharpness_factor - 0.005)
            shadow_lift *= 0.65
            highlight_recovery *= 0.65
            local_contrast_strength *= 0.60
            vibrance_strength = 0.01
        elif preset == ProcessingPreset.BALANCED:
            if metrics.dark_ratio > 0.20:
                brightness_factor += 0.015
                shadow_lift += 0.025
            contrast_factor += 0.02
            color_factor = 1.02
            sharpness_factor += 0.015
            local_contrast_strength += 0.02
            vibrance_strength = 0.035
        elif preset == ProcessingPreset.STRONG:
            if metrics.dark_ratio > 0.20:
                brightness_factor += 0.03
                shadow_lift += 0.04
            contrast_factor += 0.05
            color_factor = 1.035
            sharpness_factor += 0.03
            highlight_recovery += 0.015
            local_contrast_strength += 0.04
            vibrance_strength = 0.055

        processed = ImageEnhance.Brightness(image).enhance(brightness_factor)
        processed = ImageEnhance.Contrast(processed).enhance(contrast_factor)
        processed = processed.filter(ImageFilter.MedianFilter(size=3))
        processed = self._apply_local_tone_mapping(processed, shadow_lift, highlight_recovery)
        processed = self._apply_local_contrast(processed, local_contrast_strength)
        processed = self._apply_vibrance(processed, vibrance_strength)
        processed = ImageEnhance.Color(processed).enhance(color_factor)
        processed = processed.filter(
            ImageFilter.UnsharpMask(
                radius=1.4,
                percent=max(45, int(sharpness_factor * 55)),
                threshold=4,
            )
        )
        processed = ImageEnhance.Sharpness(processed).enhance(sharpness_factor)
        return processed

    def _apply_global_pipeline(
        self,
        image: Image.Image,
        metrics: ImageMetrics,
        preset: ProcessingPreset,
    ) -> Image.Image:
        brightness_factor = 1.0
        contrast_factor = 1.0
        color_factor = 1.0
        sharpness_factor = 1.0

        if metrics.brightness < 0.42:
            brightness_factor += 0.035
        if metrics.bright_ratio > 0.18:
            brightness_factor -= 0.02
        if metrics.contrast < 0.20:
            contrast_factor += 0.04
        if metrics.sharpness < 0.08:
            sharpness_factor += 0.02

        if preset == ProcessingPreset.GLOBAL_NATURAL:
            contrast_factor -= 0.01
            color_factor = 1.0
        elif preset == ProcessingPreset.GLOBAL_BALANCED:
            if metrics.dark_ratio > 0.20:
                brightness_factor += 0.01
            contrast_factor += 0.015
            color_factor = 1.015
            sharpness_factor += 0.01
        elif preset == ProcessingPreset.GLOBAL_STRONG:
            if metrics.dark_ratio > 0.20:
                brightness_factor += 0.02
            contrast_factor += 0.04
            color_factor = 1.03
            sharpness_factor += 0.02

        processed = ImageEnhance.Brightness(image).enhance(brightness_factor)
        processed = ImageEnhance.Contrast(processed).enhance(contrast_factor)
        processed = processed.filter(ImageFilter.MedianFilter(size=3))
        processed = ImageEnhance.Color(processed).enhance(color_factor)
        processed = processed.filter(
            ImageFilter.UnsharpMask(
                radius=1.1,
                percent=max(35, int(sharpness_factor * 45)),
                threshold=5,
            )
        )
        processed = ImageEnhance.Sharpness(processed).enhance(sharpness_factor)
        return processed

    def _normalize_preset(self, preset: ProcessingPreset) -> ProcessingPreset:
        if preset == ProcessingPreset.DEFAULT:
            return ProcessingPreset.BALANCED
        return preset

    def _is_global_preset(self, preset: ProcessingPreset) -> bool:
        return preset in {
            ProcessingPreset.GLOBAL_NATURAL,
            ProcessingPreset.GLOBAL_BALANCED,
            ProcessingPreset.GLOBAL_STRONG,
        }

    def _apply_local_tone_mapping(
        self,
        image: Image.Image,
        shadow_lift: float,
        highlight_recovery: float,
    ) -> Image.Image:
        rgb = np.asarray(image, dtype=np.float32) / 255.0
        luminance = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]

        shadow_mask = np.clip((0.50 - luminance) / 0.30, 0.0, 1.0)
        highlight_mask = np.clip((luminance - 0.72) / 0.20, 0.0, 1.0)

        adjusted_luminance = luminance
        adjusted_luminance = adjusted_luminance + shadow_lift * shadow_mask * (1.0 - adjusted_luminance) * 0.8
        adjusted_luminance = adjusted_luminance - highlight_recovery * highlight_mask * adjusted_luminance * 0.75
        adjusted_luminance = np.clip(adjusted_luminance, 0.0, 1.0)

        scale = adjusted_luminance / np.maximum(luminance, 0.05)
        toned = np.clip(rgb * scale[:, :, None], 0.0, 1.0)
        return Image.fromarray((toned * 255).astype(np.uint8), mode="RGB")

    def _apply_local_contrast(self, image: Image.Image, strength: float) -> Image.Image:
        if strength <= 0:
            return image

        rgb = np.asarray(image, dtype=np.float32) / 255.0
        base = Image.fromarray((rgb * 255).astype(np.uint8), mode="RGB")
        blurred = np.asarray(base.filter(ImageFilter.GaussianBlur(radius=14)), dtype=np.float32) / 255.0
        detail = rgb - blurred
        enhanced = np.clip(rgb + detail * strength * 1.1, 0.0, 1.0)
        return Image.fromarray((enhanced * 255).astype(np.uint8), mode="RGB")

    def _apply_vibrance(self, image: Image.Image, strength: float) -> Image.Image:
        if strength <= 0:
            return image

        rgb = np.asarray(image, dtype=np.float32) / 255.0
        max_channel = rgb.max(axis=2)
        min_channel = rgb.min(axis=2)
        saturation = np.clip(max_channel - min_channel, 0.0, 1.0)
        gray = rgb.mean(axis=2, keepdims=True)
        skin_bias = np.clip((rgb[:, :, 0] - rgb[:, :, 2]) * 1.5, 0.0, 1.0)
        per_pixel_boost = 1.0 + strength * (1.0 - saturation)[:, :, None] * (1.0 - 0.35 * skin_bias[:, :, None])
        vibrant = np.clip(gray + (rgb - gray) * per_pixel_boost, 0.0, 1.0)
        return Image.fromarray((vibrant * 255).astype(np.uint8), mode="RGB")

    def apply_logos(self, image: Image.Image, left_logo_path: str, right_logo_path: str) -> Image.Image:
        canvas = image.convert("RGBA")
        left_logo = self._set_opacity(
            self.load_logo(left_logo_path, canvas.width, canvas.height),
            self.settings.logo_opacity,
        )
        right_logo = self._set_opacity(
            self.load_logo(right_logo_path, canvas.width, canvas.height),
            self.settings.logo_opacity,
        )
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
