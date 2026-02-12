import io
from typing import List

from .parser import ParserError

# Lazy imports for optional heavy dependencies
try:
    from pdf2image import convert_from_bytes
    from PIL import Image, ImageOps, ImageFilter
    import pytesseract
    _HAS_OCR_DEPS = True
    print("[OCR] pytesseract, pdf2image, and PIL imported successfully")
except ImportError as e:
    print(f"[OCR] Warning: OCR dependencies missing: {e}")
    convert_from_bytes = None
    Image = None
    pytesseract = None
    _HAS_OCR_DEPS = False

# Optional OpenCV support for adaptive thresholding if available
try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
    print("[OCR] OpenCV available for adaptive thresholding")
except Exception:
    cv2 = None
    np = None
    _HAS_CV2 = False


def _deskew_image(img: Image.Image) -> Image.Image:
    """Try to detect orientation/rotation using Tesseract OSD and rotate to upright.

    Falls back to returning the original image if OSD is unavailable.
    """
    try:
        osd = pytesseract.image_to_osd(img)
        # Look for 'Rotate:' or 'Orientation in degrees:' lines
        for line in osd.splitlines():
            if 'Rotate:' in line:
                try:
                    angle = int(line.split(':')[-1].strip())
                    if angle and angle % 360 != 0:
                        return img.rotate(-angle, expand=True)
                except Exception:
                    continue
            if 'Orientation in degrees:' in line:
                try:
                    angle = int(line.split(':')[-1].strip())
                    if angle and angle % 360 != 0:
                        return img.rotate(-angle, expand=True)
                except Exception:
                    continue
    except Exception:
        # If any error, return original image
        return img
    return img


def _binarize_image(img: Image.Image) -> Image.Image:
    """Binarize image to improve OCR table/column layout.

    Prefer OpenCV adaptive threshold if available; otherwise use a simple global
    threshold fallback via Pillow.
    """
    try:
        # Ensure grayscale
        gray = img.convert('L')
        if _HAS_CV2 and np is not None and cv2 is not None:
            arr = np.array(gray)
            # Convert to uint8 in case
            arr = arr.astype('uint8')
            # Apply a small Gaussian blur to reduce noise
            arr = cv2.GaussianBlur(arr, (5, 5), 0)
            # Adaptive threshold (blockSize must be odd, 11 is typical)
            th = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
            return Image.fromarray(th)
        else:
            # Pillow fallback: autocontrast then global threshold
            try:
                p = ImageOps.autocontrast(gray)
                p = p.filter(ImageFilter.MedianFilter(size=3))
                # Use a conservative threshold; Otsu-like approximation via histogram
                hist = p.histogram()
                total = sum(hist)
                mean = sum(i * hist[i] for i in range(256)) / max(total, 1)
                # threshold around mean (clamped)
                thr = int(max(90, min(180, mean)))
                bw = p.point(lambda x: 255 if x > thr else 0, mode='1')
                return bw.convert('L')
            except Exception:
                return gray
    except Exception:
        return img


def ocr_pdf_bytes(file_content: bytes, dpi: int = 400, lang: str = 'eng') -> str:
    """Convert PDF bytes to images and run Tesseract OCR returning concatenated text.

    Raises ParserError if OCR dependencies are not installed or OCR fails.
    """
    if not _HAS_OCR_DEPS:
        raise ParserError("OCR dependencies are not installed. Install pytesseract, pdf2image and Pillow, and ensure Tesseract and poppler are available on the system.")

    try:
        images: List[Image.Image] = convert_from_bytes(file_content, dpi=dpi)
    except Exception as e:
        raise ParserError(f"Failed to convert PDF to images for OCR: {e}")

    texts: List[str] = []
    for img in images:
        try:
            # Deskew / detect rotation and correct
            img = _deskew_image(img)

            # Convert + preprocess: grayscale, autocontrast, median filter
            try:
                img = img.convert('L')
                img = ImageOps.autocontrast(img)
                img = img.filter(ImageFilter.MedianFilter(size=3))
                # Binarize (adaptive if OpenCV available, otherwise global threshold)
                img = _binarize_image(img)
            except Exception:
                # if preprocessing fails, proceed with original image
                pass

            # Run Tesseract on the preprocessed image
            txt = pytesseract.image_to_string(img, lang=lang)
            texts.append(txt)
        except Exception:
            texts.append("")

    return "\n".join(texts)


def ocr_image_bytes(image_bytes: bytes, lang: str = 'eng') -> str:
    """Run OCR on raw image bytes and return text."""
    if not _HAS_OCR_DEPS:
        raise ParserError("OCR dependencies are not installed. Install pytesseract and Pillow, and ensure Tesseract is available on the system.")
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = _deskew_image(img)
        try:
            img = img.convert('L')
            img = ImageOps.autocontrast(img)
            img = img.filter(ImageFilter.MedianFilter(size=3))
        except Exception:
            pass
        return pytesseract.image_to_string(img, lang=lang)
    except Exception as e:
        raise ParserError(f"Failed to OCR image bytes: {e}")


def ocr_pdf_words(file_content: bytes, dpi: int = 400, lang: str = 'eng') -> List[dict]:
    """Return OCR words with positional data using pytesseract.image_to_data.

    Each word dict contains: text, left, top, width, height, conf, page.
    """
    if not _HAS_OCR_DEPS:
        raise ParserError("OCR dependencies are not installed. Install pytesseract, pdf2image and Pillow, and ensure Tesseract and poppler are available on the system.")
    try:
        images: List[Image.Image] = convert_from_bytes(file_content, dpi=dpi)
    except Exception as e:
        raise ParserError(f"Failed to convert PDF to images for OCR: {e}")

    all_words: List[dict] = []
    for page_index, img in enumerate(images):
        try:
            img = _deskew_image(img)
            img = _binarize_image(img.convert('L'))
            data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
            n = len(data.get('text', []))
            for i in range(n):
                text = data['text'][i]
                if not text or text.strip() == '':
                    continue
                try:
                    conf = float(data.get('conf', ['0'])[i])
                except Exception:
                    conf = 0.0
                all_words.append({
                    'text': text,
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'conf': conf,
                    'page': page_index,
                })
        except Exception:
            continue

    return all_words
