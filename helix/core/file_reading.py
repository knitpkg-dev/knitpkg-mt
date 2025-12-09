from pathlib import Path
import chardet

# ==============================================================
# FILE READING
# ==============================================================

def read_file_smart(path: Path) -> str:
    """
    Read any .mqh file with the correct encoding (UTF-8, UTF-16, etc.)
    and safely remove null bytes / line-ending issues common with UTF-16 files.
    """
    raw = path.read_bytes()

    # 1. Try BOM-aware encodings first (most reliable)
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = raw.decode(encoding)
            # Normalize line endings and strip null bytes left by UTF-16
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = text.replace("\x00", "")
            return text
        except UnicodeDecodeError:
            continue

    # 2. Fallback to chardet detection
    detected = chardet.detect(raw)
    encoding = detected["encoding"] or "utf-8"
    try:
        text = raw.decode(encoding)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", "")
        return text
    except:
        pass

    # 3. Last resort: force UTF-8 with replacement
    text = raw.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    return text
