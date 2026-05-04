"""
RTL & BiDi Text Formatter for Persian Subtitles in Unity TextMeshPro
Handles Persian character extensions, ligature joining, and visual BiDi reordering.
"""

import arabic_reshaper
from bidi.algorithm import get_display

_reshaper_config = {
    'support_ligatures': True,
    'support_transparent': True,
    'delete_harakat': True,
    'shift_harakat_position': False,
    'use_unshaped_instead_of_isolated': False,
    'enable_formatting': True
}
_reshaper = arabic_reshaper.ArabicReshaper(configuration=_reshaper_config)


def shape_persian(text: str) -> str:
    """
    Takes standard Persian text and converts it into visually ordered,
    connected Arabic/Persian presentation forms for Unity TextMeshPro.
    """
    if not text or not text.strip():
        return text

    # Handle multi-line subtitles
    lines = text.split('\n')
    shaped_lines = []
    for line in lines:
        if not line.strip():
            shaped_lines.append(line)
            continue
        reshaped = _reshaper.reshape(line)
        bidi_ordered = get_display(reshaped)
        shaped_lines.append(bidi_ordered)

    return '\n'.join(shaped_lines)


if __name__ == '__main__':
    sample = "انگاری دستم یه خورده بی‌حس شده..."
    print("Original:", sample)
    print("Shaped:  ", shape_persian(sample))
