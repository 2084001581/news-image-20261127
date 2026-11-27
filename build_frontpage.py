#!/usr/bin/env python3
"""Render the front page of THE WORLD TODAY for Friday, 27 November 2026.

The script composes a 1024x1024 newspaper front page from three
illustration stills in assets/ plus vector type, and writes entry.png
next to itself. It is written from scratch for this entry: the layout
is a top-down flow -- masthead, date bar, hero photo, lead story, two
photo stories, two text stories, an "also today" strip, footer -- with
a running vertical cursor, so every block is placed by measuring the
text that came before it instead of hard-coding absolute coordinates.

Run:  python3 build_frontpage.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

# --- page geometry -------------------------------------------------------
PAGE_W, PAGE_H = 1024, 1024
MARGIN = 30                      # side margin; text never crosses it
CONTENT_W = PAGE_W - 2 * MARGIN  # 964
GAP = 24                         # gutter between the two columns
COL_W = (CONTENT_W - GAP) // 2   # 470

# --- palette -------------------------------------------------------------
PAPER = (248, 242, 228)   # warm newsprint cream
INK = (17, 17, 17)        # near-black type
RULE = (17, 17, 17)
KICKER_RED = (158, 17, 17)   # dark red section labels
GOLD = (242, 194, 48)     # "ALSO TODAY:" label on the black strip
GREY = (110, 105, 95)     # footer small print

# --- fonts ---------------------------------------------------------------
LIBERATION = "/usr/share/fonts/truetype/liberation"


def typeface(kind, size):
    """Load a Liberation face. kind is one of serif, serif-bold,
    serif-italic, sans, sans-bold."""
    names = {
        "serif": "LiberationSerif-Regular.ttf",
        "serif-bold": "LiberationSerif-Bold.ttf",
        "serif-italic": "LiberationSerif-Italic.ttf",
        "sans": "LiberationSans-Regular.ttf",
        "sans-bold": "LiberationSans-Bold.ttf",
    }
    return ImageFont.truetype(os.path.join(LIBERATION, names[kind]), size)


# --- text helpers --------------------------------------------------------
def wrap_words(draw, text, font, max_width):
    """Greedy word wrap. Returns a list of lines that each fit max_width."""
    lines, current = [], ""
    for word in text.split(" "):
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_lines(draw, lines, x, y, font, fill, leading):
    """Draw stacked lines; return the y just below the last line."""
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += leading
    return y


def balanced_wrap(draw, text, font, max_width):
    """Split a short headline into two lines of near-equal width.
    Tries every word boundary and keeps the split whose longer line is
    shortest; falls back to a plain greedy wrap if nothing fits."""
    words = text.split(" ")
    best = None
    for cut in range(1, len(words)):
        first = " ".join(words[:cut])
        second = " ".join(words[cut:])
        widest = max(draw.textlength(first, font=font),
                     draw.textlength(second, font=font))
        if widest <= max_width and (best is None or widest < best[0]):
            best = (widest, [first, second])
    if best is not None:
        return best[1]
    return wrap_words(draw, text, font, max_width)


def headline_that_fits(draw, text, kind, start_size, max_width, max_lines,
                       min_size=18):
    """Shrink a headline until it wraps into at most max_lines lines."""
    size = start_size
    while size > min_size:
        font = typeface(kind, size)
        lines = wrap_words(draw, text, font, max_width)
        if len(lines) <= max_lines:
            return font, lines, size
        size -= 1
    font = typeface(kind, min_size)
    return font, wrap_words(draw, text, font, max_width), min_size


# --- photo helper --------------------------------------------------------
def cover_crop(photo, target_w, target_h, focus_y=0.45):
    """Scale a photo to cover the target box, then centre-crop it.
    focus_y (0..1) slides the crop window down the source image, so a
    wide letterbox crop can keep the building / horizon in frame."""
    src_w, src_h = photo.size
    scale = max(target_w / src_w, target_h / src_h)
    grown = photo.resize((round(src_w * scale), round(src_h * scale)),
                         Image.Resampling.LANCZOS)
    gw, gh = grown.size
    left = (gw - target_w) // 2
    top = int((gh - target_h) * focus_y)
    top = max(0, min(top, gh - target_h))
    return grown.crop((left, top, left + target_w, top + target_h))


def load_photo(filename):
    path = os.path.join(ASSETS, filename)
    return Image.open(path).convert("RGB")


# --- story copy (facts as listed in README.md) ---------------------------
LEAD_CAPTION = ("Parliament in Wellington. Labour won the popular vote "
                "but lacks the seats to govern.")
LEAD_HEADLINE = "NEW ZEALAND COALITION ONE SEAT SHORT"
LEAD_DECK = ("Final count gives Luxon's National-led bloc 65 of 130 seats. "
             "It must win over the centrist Opportunity Party "
             "\u2014 or face another election.")

STORM = {
    "kicker": "UNITED STATES",
    "headline": "Thanksgiving storm strands travellers",
    "body": ("About 400 flights cancelled and 724,000 homes lose power "
             "on the East Coast; New York postpones its parade."),
    "photo": "media-generation-storm-us-east-coast-0-af9f8f58-eb11-4335-8065-5b0e96e9b8b4.png",
}
OIL = {
    "kicker": "ENERGY",
    "headline": "Oil nears $97 as attacks threaten supply",
    "body": ("Brent climbs on strikes on tankers in the Strait of Hormuz "
             "and on Saudi energy sites; still down about 18% for "
             "the month."),
    "photo": "media-generation-oil-tanker-hormuz-0-6d5c060c-914c-48f5-ba1d-32a15a85594f.png",
}
UKRAINE = {
    "kicker": "UKRAINE",
    "headline": "Trump tells Putin to \u201cpull back\u201d in Europe",
    "body": ("Zelenskyy warns of a new mass Russian strike in the coming "
             "days after missiles hit Kyiv, wounding seven."),
}
ARGENTINA = {
    "kicker": "ARGENTINA",
    "headline": "Central bank barred from printing money",
    "body": ("Lower house votes to stop the bank funding government "
             "spending, aiming to lock in the fight against inflation."),
}

ALSO_LABEL = "ALSO TODAY:  "
ALSO_TEXT = ("Hasina sets 16 Dec return to Bangladesh \u2022 AFP takes "
             "site offline after cyberattack \u2022 Seoul sends six North "
             "Koreans home \u2022 EU leaders split over $49bn Ukraine loan")
FOOTER = ("All stories happened or were first reported on "
          "Friday, 27 November 2026.")


# --- the page ------------------------------------------------------------
def build_page():
    page = Image.new("RGB", (PAGE_W, PAGE_H), PAPER)
    draw = ImageDraw.Draw(page)
    y = 18  # top pad

    # Masthead.
    masthead = typeface("serif-bold", 64)
    title = "THE WORLD TODAY"
    draw.text(((PAGE_W - draw.textlength(title, font=masthead)) / 2, y),
              title, font=masthead, fill=INK)
    y += 76

    # Thin rule, black date bar, thin rule.
    draw.rectangle([MARGIN, y, PAGE_W - MARGIN, y + 2], fill=RULE)
    y += 7
    bar_h = 42
    draw.rectangle([MARGIN, y, PAGE_W - MARGIN, y + bar_h], fill=INK)
    date_font = typeface("sans-bold", 24)
    date_text = "FRIDAY  \u2022  27 NOVEMBER 2026"
    draw.text(((PAGE_W - draw.textlength(date_text, font=date_font)) / 2,
               y + 8), date_text, font=date_font, fill=PAPER)
    y += bar_h + 5
    draw.rectangle([MARGIN, y, PAGE_W - MARGIN, y + 2], fill=RULE)
    y += 10

    # Hero photo: Wellington's Parliament Buildings, letterboxed.
    hero = load_photo("media-generation-hero-wellington-parliament-0-ddc41294-4303-4692-b858-343cbaf2c54e.png")
    page.paste(cover_crop(hero, CONTENT_W, 178, focus_y=0.10),
               (MARGIN, y))
    y += 178 + 7

    # Photo caption.
    caption_font = typeface("serif-italic", 19)
    draw.text((MARGIN, y), LEAD_CAPTION, font=caption_font, fill=INK)
    y += 27

    # Lead headline (two balanced lines) and deck.
    head_font = typeface("serif-bold", 43)
    head_lines = balanced_wrap(draw, LEAD_HEADLINE, head_font, CONTENT_W)
    y = draw_lines(draw, head_lines, MARGIN, y, head_font, INK, 48)
    y += 5
    deck_font = typeface("serif", 23)
    deck_lines = wrap_words(draw, LEAD_DECK, deck_font, CONTENT_W)
    y = draw_lines(draw, deck_lines, MARGIN, y, deck_font, INK, 29)
    y += 9

    # Rule above the photo stories.
    draw.rectangle([MARGIN, y, PAGE_W - MARGIN, y + 2], fill=RULE)
    y += 10

    # Two photo stories side by side.
    photo_h = 122
    for story, x in ((STORM, MARGIN),
                     (OIL, MARGIN + COL_W + GAP)):
        photo = load_photo(story["photo"])
        page.paste(cover_crop(photo, COL_W, photo_h, focus_y=0.5), (x, y))
    y += photo_h + 8

    # Kickers, headlines, bodies for the two photo stories. The row is as
    # tall as the taller column, so measure both before moving on.
    row_bottom = y
    for story, x in ((STORM, MARGIN),
                     (OIL, MARGIN + COL_W + GAP)):
        cy = y
        kicker_font = typeface("sans-bold", 18)
        draw.text((x, cy), story["kicker"], font=kicker_font,
                  fill=KICKER_RED)
        cy += 24
        h_font, h_lines, _ = headline_that_fits(
            draw, story["headline"], "serif-bold", 25, COL_W, 2)
        cy = draw_lines(draw, h_lines, x, cy, h_font, INK, 29)
        cy += 3
        body_font = typeface("serif", 18)
        body_lines = wrap_words(draw, story["body"], body_font, COL_W)
        cy = draw_lines(draw, body_lines, x, cy, body_font, INK, 23)
        row_bottom = max(row_bottom, cy)
    y = row_bottom + 9

    # Rule above the text-only stories.
    draw.rectangle([MARGIN, y, PAGE_W - MARGIN, y + 2], fill=RULE)
    y += 10

    # Two text-only stories side by side.
    row_bottom = y
    for story, x in ((UKRAINE, MARGIN),
                     (ARGENTINA, MARGIN + COL_W + GAP)):
        cy = y
        kicker_font = typeface("sans-bold", 18)
        draw.text((x, cy), story["kicker"], font=kicker_font,
                  fill=KICKER_RED)
        cy += 24
        h_font, h_lines, _ = headline_that_fits(
            draw, story["headline"], "serif-bold", 24, COL_W, 2)
        cy = draw_lines(draw, h_lines, x, cy, h_font, INK, 28)
        cy += 3
        body_font = typeface("serif", 18)
        body_lines = wrap_words(draw, story["body"], body_font, COL_W)
        cy = draw_lines(draw, body_lines, x, cy, body_font, INK, 23)
        row_bottom = max(row_bottom, cy)
    y = row_bottom + 11

    # "Also today" black strip. The gold label leads the first line and
    # the items flow after it, separated by bullets.
    strip_font = typeface("sans", 18)
    label_font = typeface("sans-bold", 18)
    words = ALSO_TEXT.split(" ")
    # Build styled tokens: (word, font, fill). The label is one token.
    tokens = [(ALSO_LABEL, label_font, GOLD)]
    tokens += [(w, strip_font, PAPER) for w in words]
    strip_lines = []
    current, current_w = [], 0
    space_w = draw.textlength(" ", font=strip_font)
    for word, font, fill in tokens:
        w = draw.textlength(word, font=font)
        extra = 0 if not current else space_w
        if current_w + extra + w <= CONTENT_W - 24:
            current.append((word, font, fill))
            current_w += extra + w
        else:
            strip_lines.append(current)
            current = [(word, font, fill)]
            current_w = w
    if current:
        strip_lines.append(current)
    strip_h = 12 + len(strip_lines) * 23 + 10
    draw.rectangle([MARGIN, y, PAGE_W - MARGIN, y + strip_h], fill=INK)
    ly = y + 11
    for line in strip_lines:
        lx = MARGIN + 12
        for word, font, fill in line:
            draw.text((lx, ly), word, font=font, fill=fill)
            lx += draw.textlength(word, font=font) + space_w
        ly += 23
    y += strip_h + 9

    # Footer small print, centred.
    footer_font = typeface("serif-italic", 16)
    draw.text(((PAGE_W - draw.textlength(FOOTER, font=footer_font)) / 2, y),
              FOOTER, font=footer_font, fill=GREY)
    y += 20

    print("bottom cursor y =", y, "page height =", PAGE_H)
    return page


def main():
    page = build_page()
    out_path = os.path.join(HERE, "entry.png")
    page.save(out_path, format="PNG")
    print("wrote", out_path, page.size,
          os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    main()
