import threading
from typing import List, Tuple

from app.services.gpu_gate import gpu_gate, gpu_enabled

_reader_lock = threading.Lock()
_readers = {}  # (langs_tuple, use_gpu) -> easyocr.Reader


def _get_reader(langs: Tuple[str, ...], use_gpu: bool):
    key = (langs, use_gpu)
    with _reader_lock:
        if key in _readers:
            return _readers[key]

    import easyocr

    if use_gpu:
        with gpu_gate.use("easyocr_init"):
            reader = easyocr.Reader(list(langs), gpu=True)
    else:
        reader = easyocr.Reader(list(langs), gpu=False)

    with _reader_lock:
        _readers[key] = reader
    return reader


def readtext_image_file(
    file_path: str,
    langs: List[str] | None = None,
    *,
    detail: int = 0,
    paragraph: bool = False,
) -> List[str]:
    """
    Read text from an image file using a cached EasyOCR reader.
    Uses GPU only if CUDA is available (or forced via SRRIS_GPU_MODE=force).
    """
    langs_tuple = tuple(langs or ["en"])
    use_gpu = gpu_enabled()
    reader = _get_reader(langs_tuple, use_gpu)

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    if use_gpu:
        with gpu_gate.use("easyocr_infer"):
            return reader.readtext(img_bytes, detail=detail, paragraph=paragraph)
    return reader.readtext(img_bytes, detail=detail, paragraph=paragraph)

