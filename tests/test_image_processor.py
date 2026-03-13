from pathlib import Path

from PIL import Image

from app.enums import ProcessingPreset
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

