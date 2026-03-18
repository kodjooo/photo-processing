from pathlib import Path
from types import SimpleNamespace

import numpy as np

from PIL import Image, ImageStat

from app.enums import ProcessingPreset
from app.processing import images as images_module
from app.processing.images import ImageProcessor


def test_image_processor_creates_output_file(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jpg"
    target_path = tmp_path / "target.jpg"
    left_logo = tmp_path / "left.png"
    right_logo = tmp_path / "right.png"

    Image.new("RGB", (640, 480), (120, 130, 140)).save(source_path)
    Image.new("RGBA", (120, 40), (255, 255, 255, 255)).save(left_logo)
    Image.new("RGBA", (120, 40), (255, 255, 255, 255)).save(right_logo)

    processor = ImageProcessor()
    processor.process_image(
        source_path,
        target_path,
        preset=ProcessingPreset.DEFAULT,
        left_logo_path=str(left_logo),
        right_logo_path=str(right_logo),
    )

    assert target_path.exists()
    result = Image.open(target_path)
    assert result.size == (640, 480)


def test_image_processor_supports_raw_input(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "source.cr2"
    target_path = tmp_path / "target.jpg"
    left_logo = tmp_path / "left.png"
    right_logo = tmp_path / "right.png"

    source_path.write_bytes(b"raw")
    Image.new("RGBA", (120, 40), (255, 255, 255, 255)).save(left_logo)
    Image.new("RGBA", (120, 40), (255, 255, 255, 255)).save(right_logo)

    class FakeRaw:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def postprocess(self, **kwargs):
            return np.full((200, 300, 3), 128, dtype=np.uint8)

    monkeypatch.setattr(images_module, "rawpy", SimpleNamespace(imread=lambda _: FakeRaw()))

    processor = ImageProcessor()
    processor.process_image(
        source_path,
        target_path,
        preset=ProcessingPreset.DEFAULT,
        left_logo_path=str(left_logo),
        right_logo_path=str(right_logo),
    )

    assert target_path.exists()
    result = Image.open(target_path)
    assert result.size == (300, 200)


def test_export_decoded_image_supports_raw_without_postprocessing(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "source.cr2"
    auto_target_path = tmp_path / "decoded-auto.jpg"
    natural_target_path = tmp_path / "decoded-natural.jpg"

    source_path.write_bytes(b"raw")

    class FakeRaw:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def postprocess(self, **kwargs):
            value = 170 if not kwargs["no_auto_bright"] else 120
            return np.full((100, 140, 3), value, dtype=np.uint8)

    monkeypatch.setattr(images_module, "rawpy", SimpleNamespace(imread=lambda _: FakeRaw()))

    processor = ImageProcessor()
    processor.export_decoded_image(source_path, auto_target_path, raw_auto_bright=True)
    processor.export_decoded_image(source_path, natural_target_path, raw_auto_bright=False)

    auto_result = np.asarray(Image.open(auto_target_path), dtype=np.float32)
    natural_result = np.asarray(Image.open(natural_target_path), dtype=np.float32)

    assert auto_target_path.exists()
    assert natural_target_path.exists()
    assert auto_result.mean() > natural_result.mean()


def test_load_logo_uses_horizontal_ratio_for_landscape(tmp_path: Path) -> None:
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (200, 100), (255, 255, 255, 255)).save(logo_path)

    processor = ImageProcessor()
    resized = processor.load_logo(str(logo_path), base_width=1000, base_height=600)

    assert resized.width == 150


def test_load_logo_uses_vertical_ratio_for_portrait(tmp_path: Path) -> None:
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (200, 100), (255, 255, 255, 255)).save(logo_path)

    processor = ImageProcessor()
    resized = processor.load_logo(str(logo_path), base_width=800, base_height=1200)

    assert resized.width == 200


def test_strong_preset_is_more_aggressive_than_natural() -> None:
    processor = ImageProcessor()
    image = Image.new("RGB", (200, 120), (90, 100, 110))
    metrics = processor.calculate_metrics(image)

    natural = processor.apply_pipeline(image, metrics, ProcessingPreset.NATURAL)
    strong = processor.apply_pipeline(image, metrics, ProcessingPreset.STRONG)

    natural_stat = ImageStat.Stat(natural)
    strong_stat = ImageStat.Stat(strong)

    assert sum(strong_stat.mean) > sum(natural_stat.mean)


def test_adaptive_pipeline_lifts_shadows_more_than_highlights() -> None:
    processor = ImageProcessor()
    gradient = np.tile(np.linspace(20, 240, 256, dtype=np.uint8), (64, 1))
    image = Image.fromarray(np.stack([gradient, gradient, gradient], axis=2), mode="RGB")
    metrics = processor.calculate_metrics(image)

    processed = processor.apply_pipeline(image, metrics, ProcessingPreset.BALANCED)

    original = np.asarray(image, dtype=np.float32)
    enhanced = np.asarray(processed, dtype=np.float32)

    shadow_gain = enhanced[:, :32].mean() - original[:, :32].mean()
    highlight_gain = enhanced[:, -32:].mean() - original[:, -32:].mean()

    assert shadow_gain > 0
    assert shadow_gain > highlight_gain


def test_local_contrast_changes_midtones_without_blowing_out_highlights() -> None:
    processor = ImageProcessor()
    image = Image.new("RGB", (120, 120), (150, 150, 150))
    for x in range(40, 80):
        for y in range(40, 80):
            image.putpixel((x, y), (175, 175, 175))

    metrics = processor.calculate_metrics(image)
    processed = processor.apply_pipeline(image, metrics, ProcessingPreset.STRONG)

    original = np.asarray(image, dtype=np.float32)
    enhanced = np.asarray(processed, dtype=np.float32)

    center_delta = enhanced[45:75, 45:75].mean() - original[45:75, 45:75].mean()
    corner_delta = enhanced[:20, :20].mean() - original[:20, :20].mean()

    assert center_delta != 0
    assert abs(center_delta - corner_delta) > 0.5


def test_global_strong_is_more_uniform_than_local_strong() -> None:
    processor = ImageProcessor()
    image = Image.new("RGB", (120, 120), (150, 150, 150))
    for x in range(40, 80):
        for y in range(40, 80):
            image.putpixel((x, y), (175, 175, 175))

    metrics = processor.calculate_metrics(image)
    local_processed = processor.apply_pipeline(image, metrics, ProcessingPreset.STRONG)
    global_processed = processor.apply_pipeline(image, metrics, ProcessingPreset.GLOBAL_STRONG)

    original = np.asarray(image, dtype=np.float32)
    local_enhanced = np.asarray(local_processed, dtype=np.float32)
    global_enhanced = np.asarray(global_processed, dtype=np.float32)

    local_delta = (
        local_enhanced[45:75, 45:75].mean() - original[45:75, 45:75].mean()
    ) - (
        local_enhanced[:20, :20].mean() - original[:20, :20].mean()
    )
    global_delta = (
        global_enhanced[45:75, 45:75].mean() - original[45:75, 45:75].mean()
    ) - (
        global_enhanced[:20, :20].mean() - original[:20, :20].mean()
    )

    assert abs(local_delta) > abs(global_delta)
