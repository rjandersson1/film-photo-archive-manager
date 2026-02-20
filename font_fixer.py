from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen


def _empty_glyph():
    pen = TTGlyphPen(None)
    return pen.glyph()


def make_allcaps_font(in_path: str, out_path: str) -> None:
    font = TTFont(in_path)

    if "cmap" not in font or "glyf" not in font or "hmtx" not in font:
        raise ValueError("Font must contain cmap, glyf, and hmtx tables (TrueType outlines).")

    glyf = font["glyf"]
    hmtx = font["hmtx"]
    glyph_order = font.getGlyphOrder()

    # Pick a Unicode cmap subtable to edit (prefer Windows Unicode BMP/full).
    cmap_table = font["cmap"]
    subtables = sorted(
        cmap_table.tables,
        key=lambda t: (
            0 if (t.platformID == 3 and t.platEncID in (1, 10)) else 1,
            0 if t.isUnicode() else 1,
        ),
    )
    cmap_sub = None
    for st in subtables:
        if st.isUnicode():
            cmap_sub = st
            break
    if cmap_sub is None:
        raise ValueError("No Unicode cmap subtable found.")

    cmap = cmap_sub.cmap  # dict: codepoint -> glyphName

    def glyph_for_codepoint(cp: int) -> str | None:
        return cmap.get(cp)

    def ensure_glyph(name: str) -> None:
        if name not in glyph_order:
            glyph_order.append(name)
            glyf.glyphs[name] = _empty_glyph()
            hmtx.metrics[name] = (0, 0)

    # Copy A-Z glyphs/metrics into a-z codepoints.
    for i in range(26):
        cp_upper = ord("A") + i
        cp_lower = ord("a") + i

        g_upper = glyph_for_codepoint(cp_upper)
        if g_upper is None:
            continue

        g_lower = glyph_for_codepoint(cp_lower)

        # If lowercase codepoint has no glyph, create a new glyph name.
        if g_lower is None:
            # Create a new glyph name that won't collide.
            new_name = f"{g_upper}.lc"
            ensure_glyph(new_name)
            g_lower = new_name
            cmap[cp_lower] = g_lower

        # Copy outlines and metrics.
        import copy
        glyf.glyphs[g_lower] = copy.deepcopy(glyf.glyphs[g_upper])
        hmtx.metrics[g_lower] = hmtx.metrics[g_upper]

    font.setGlyphOrder(glyph_order)
    font.save(out_path)


if __name__ == "__main__":
    # Example:
    # make_allcaps_font("/path/to/input.ttf", "/path/to/output_allcaps.ttf")
    import sys


    input_font = "fonts/JMH Typewriter mono Bold.ttf"
    output_font = "fonts/JMH Typewriter mono Bold allcaps.ttf"
    # if len(sys.argv) != 3:
    #     raise SystemExit("Usage: python make_allcaps.py /path/to/input.ttf /path/to/output.ttf")

    make_allcaps_font(input_font, output_font)
    print("done")