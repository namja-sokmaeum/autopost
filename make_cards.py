"""@namja_sokmaeum 카드뉴스 생성기

사용법: python3 make_cards.py posts.json out/
posts.json 형식은 함께 있는 예시 파일 참고.
[대괄호]로 감싼 글자는 강조색으로 표시됩니다.
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350  # 인스타 세로형 4:5
BG = "#F6F1E7"
INK = "#1E2A44"
SUB = "#6B7385"
ACCENT = "#2F6BFF"
HANDLE = "@namja_sokmaeum"
MARGIN = 110

FONT_DIR = "/usr/share/fonts/opentype/noto/"
KR = 1  # Noto CJK 컬렉션의 한국어 인덱스


def font(weight, size):
    name = {"black": "NotoSansCJK-Black.ttc", "bold": "NotoSansCJK-Bold.ttc",
            "regular": "NotoSansCJK-Regular.ttc"}[weight]
    return ImageFont.truetype(FONT_DIR + name, size, index=KR)


def parse(text):
    """'[강조] 일반' -> [(글자, 강조여부), ...]"""
    out = []
    for part in re.split(r"(\[[^\]]*\])", text):
        if part.startswith("[") and part.endswith("]"):
            out += [(c, True) for c in part[1:-1]]
        else:
            out += [(c, False) for c in part]
    return out


def wrap(chars, f, max_w):
    """단어(공백) 단위 줄바꿈, 너무 긴 단어는 글자 단위로 자름."""
    lines, line, word = [], [], []

    def width(cs):
        return f.getlength("".join(c for c, _ in cs))

    def flush_word():
        nonlocal line, word
        if not word:
            return
        cand = line + word
        if width(cand) <= max_w or not line:
            line = cand
            # 한 단어가 한 줄보다 길면 글자 단위로 자르기
            while width(line) > max_w:
                cut = len(line)
                while cut > 1 and width(line[:cut]) > max_w:
                    cut -= 1
                lines.append(line[:cut])
                line = line[cut:]
        else:
            while line and line[-1][0] == " ":
                line = line[:-1]
            lines.append(line)
            line = word[:]
        word = []

    for c in chars:
        if c[0] == "\n":
            flush_word()
            lines.append(line)
            line = []
        elif c[0] == " ":
            flush_word()
            line.append(c)
        else:
            word.append(c)
    flush_word()
    lines.append(line)
    return [l[1:] if l and l[0][0] == " " else l for l in lines]


def draw_text(d, xy, text, f, max_w, color=INK, gap=1.45, align="left", anchor="la"):
    x0, y = xy
    lh = f.size * gap
    for line in wrap(parse(text), f, max_w):
        lw = f.getlength("".join(c for c, _ in line))
        x = x0 + (max_w - lw) / 2 if align == "center" else x0
        for c, hl in line:
            d.text((x, y), c, font=f, fill=ACCENT if hl else color, anchor=anchor)
            x += f.getlength(c)
        y += lh
    return y


def draw_centered(d, box, text, f, color, gap=1.5):
    """박스(x0, y0, x1, y1) 안에 여러 줄 텍스트를 가로·세로 정중앙 배치."""
    x0, y0, x1, y1 = box
    n = len(wrap(parse(text), f, x1 - x0))
    lh = f.size * gap
    first = (y0 + y1) / 2 - (n - 1) * lh / 2
    draw_text(d, (x0, first), text, f, x1 - x0, color=color, gap=gap, align="center", anchor="lm")


def text_height(text, f, max_w, gap=1.45):
    return len(wrap(parse(text), f, max_w)) * f.size * gap


def frame(page, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # 하단: 핸들 + 페이지
    f = font("regular", 26)
    d.text((MARGIN, H - 110), HANDLE, font=f, fill=SUB)
    if total > 1:
        p = f"{page} / {total}"
        d.text((W - MARGIN - f.getlength(p), H - 110), p, font=f, fill=SUB)
    return img, d


def cover(s, page, total):
    img, d = frame(page, total)
    mw = W - MARGIN * 2
    ft, fs = font("black", 92), font("regular", 36)
    th = text_height(s["title"], ft, mw, 1.3)
    sh = text_height(s.get("sub", ""), fs, mw) if s.get("sub") else 0
    y = (H - th - sh - 60) / 2
    y = draw_text(d, (MARGIN, y), s["title"], ft, mw, gap=1.3)
    if s.get("sub"):
        draw_text(d, (MARGIN, y + 50), s["sub"], fs, mw, color=SUB)
    return img


def item(s, page, total):
    img, d = frame(page, total)
    mw = W - MARGIN * 2
    fn, fh, fb = font("black", 150), font("bold", 64), font("regular", 40)
    hh = text_height(s["head"], fh, mw, 1.35)
    bh = text_height(s["body"], fb, mw, 1.6)
    y = (H - (190 + hh + 50 + bh)) / 2
    d.text((MARGIN, y), f"{s['num']:02d}", font=fn, fill=ACCENT)
    y += 190
    y = draw_text(d, (MARGIN, y), s["head"], fh, mw, gap=1.35)
    d.line((MARGIN, y + 20, MARGIN + 80, y + 20), fill=INK, width=4)
    draw_text(d, (MARGIN, y + 50), s["body"], fb, mw, color="#3A4458", gap=1.6)
    return img


def ending(s, page, total):
    img, d = frame(page, total)
    mw = W - MARGIN * 2
    ft, fs = font("black", 78), font("bold", 40)
    th = text_height(s["title"], ft, mw, 1.3)
    y = (H - th - 260) / 2
    y = draw_text(d, (MARGIN, y), s["title"], ft, mw, gap=1.3, align="center")
    # 행동 유도 박스
    box_y = y + 60
    d.rounded_rectangle((MARGIN, box_y, W - MARGIN, box_y + 170), radius=36, fill=INK)
    draw_centered(d, (MARGIN + 50, box_y, W - MARGIN - 50, box_y + 170), s["cta"], fs,
                  "#FFFFFF")
    return img


def single(s, page, total):
    """한 장에 제목 + 항목 목록 + 행동 유도를 모두 넣는 레이아웃."""
    img, d = frame(page, total)
    mw = W - MARGIN * 2
    ft = font("black", 64)
    fn, fh, fb = font("black", 40), font("bold", 39), font("regular", 29)
    fc = font("bold", 34)
    num_w = 86

    # 전체 높이를 먼저 계산해서 세로 가운데 정렬
    th = text_height(s["title"], ft, mw, 1.28)
    rows = []
    for it in s["items"]:
        hh = text_height(it["head"], fh, mw - num_w, 1.3)
        bh = text_height(it.get("body", ""), fb, mw - num_w, 1.45) if it.get("body") else 0
        rows.append((it, hh, bh))
    row_gap = 28
    list_h = sum(hh + bh + 8 for _, hh, bh in rows) + row_gap * (len(rows) - 1)
    cta_h = 100 if s.get("cta") else 0
    total_h = th + 56 + list_h + (56 + cta_h if cta_h else 0)
    top, bottom = 130, H - 160  # 상단 마크와 하단 핸들 사이
    y = top + max(0, (bottom - top - total_h) / 2)

    y = draw_text(d, (MARGIN, y), s["title"], ft, mw, gap=1.28)
    y += 18
    d.line((MARGIN, y, W - MARGIN, y), fill="#D9D2C3", width=3)
    y += 38

    for i, (it, hh, bh) in enumerate(rows, 1):
        d.text((MARGIN, y - 2), f"{i:02d}", font=fn, fill=ACCENT)
        yy = draw_text(d, (MARGIN + num_w, y), it["head"], fh, mw - num_w, gap=1.3)
        if it.get("body"):
            yy = draw_text(d, (MARGIN + num_w, yy + 8), it["body"], fb, mw - num_w,
                           color="#4A5368", gap=1.45)
        y = yy + row_gap

    if s.get("cta"):
        y += 14
        d.rounded_rectangle((MARGIN, y, W - MARGIN, y + cta_h), radius=56, fill=INK)
        draw_centered(d, (MARGIN, y, W - MARGIN, y + cta_h), s["cta"], fc, "#FFFFFF")
    return img


RENDER = {"cover": cover, "item": item, "ending": ending, "single": single}


def main(src, out_dir):
    posts = json.loads(Path(src).read_text(encoding="utf-8"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for post in posts:
        slides = post["slides"]
        for i, s in enumerate(slides, 1):
            img = RENDER[s["type"]](s, i, len(slides))
            # 인스타그램 API는 JPEG만 받음
            path = out / f"{post['id']}_{i:02d}.jpg"
            img.save(path, "JPEG", quality=95)
            print(path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "posts.json",
         sys.argv[2] if len(sys.argv) > 2 else "out")
