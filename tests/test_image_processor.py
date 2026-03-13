from pathlib import Path
from types import SimpleNamespace

import numpy as np

from PIL import Image

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
