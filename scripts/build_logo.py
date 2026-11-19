#!/usr/bin/env python3
"""Draw the FTreeKG logo in Art Techno and write every size the repo uses.

The mark is the listing: a directory listing drawn as traces, the way the
``tree`` command prints it. The root is the die; one rail runs down from it,
with right-angle branches to folders and files, and each folder holds its own
entries. The palette, drawing helpers and outlined lettering come from the
Art Techno brand build, so the SVGs render the same everywhere.

Usage::

    python scripts/build_logo.py

Needs ``fonttools``, Google Chrome for the PNG renders, and a clone of
https://github.com/Flux-Frontiers/art_techno beside this repo. Set ``CHROME``
to the browser binary if it is not at the default macOS path.

Writes:

- ``assets/ftreekg_logo.svg`` and ``assets/ftreekg_logo.png``: the square mark
  (1024 px PNG)
- ``assets/ftreekg_icon.svg``: the mark reduced for 64 px and below
- ``assets/ftreekg_banner.svg`` and ``assets/ftreekg_banner.png``
"""

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AT_BUILD = ROOT.parent / "art_techno" / "docs" / "brand" / "build.py"

_spec = importlib.util.spec_from_file_location("at_build", AT_BUILD)
at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(at)

f, line, pad, via, diamond, clipped_rect = (
    at.f,
    at.line,
    at.pad,
    at.via,
    at.diamond,
    at.clipped_rect,
)
OBSIDIAN, PANEL, COPPER, GOLD, GREEN, MINT, SILK = (
    at.OBSIDIAN,
    at.PANEL,
    at.COPPER,
    at.GOLD,
    at.GREEN,
    at.MINT,
    at.SILK,
)

NAME = "FTREEKG"
PART = "EVERY FILE A NODE"


def rect(
    x: float, y: float, w: float, h: float, fill: str, stroke: str = "", width: float = 0
) -> str:
    s = f' stroke="{stroke}" stroke-width="{f(width)}"' if stroke else ""
    return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{fill}"{s}/>'


def package(x: float, y: float, r: float, c: float, width: float) -> str:
    """A chip package: a dark square with 45-degree corners in a gold line.

    :param x: Center x.
    :param y: Center y.
    :param r: Half the side length.
    :param c: Corner cut.
    :param width: Stroke width.
    """
    return (
        f'<path d="{clipped_rect(x - r, y - r, 2 * r, 2 * r, c)}" fill="{PANEL}" '
        f'stroke="{GOLD}" stroke-width="{f(width)}"/>'
    )


def die(x: float, y: float, s: float, core: str) -> str:
    """A square green die in a gold line, centered on ``x, y``.

    :param x: Center x.
    :param y: Center y.
    :param s: Side length.
    :param core: Color of the square at its center.
    """
    return rect(x - s / 2, y - s / 2, s, s, GREEN, GOLD, s / 9) + rect(
        x - s / 6, y - s / 6, s / 3, s / 3, core
    )


def node(x: float, y: float, r: float) -> str:
    """A file: a gold pad with a green core."""
    return pad(x, y, r, GOLD) + pad(x, y, r * 0.44, GREEN)


def folder(x: float, y: float, w: float, h: float, color: str, width: float) -> str:
    """A folder: a body with a clipped tab on its upper left."""
    tab = w * 0.42
    pts = [
        (x, y),
        (x + tab - h * 0.18, y),
        (x + tab, y + h * 0.18),
        (x + w, y + h * 0.18),
        (x + w, y + h),
        (x, y + h),
    ]
    d = "M" + "L".join(f"{f(px)} {f(py)}" for px, py in pts) + "Z"
    return (
        f'<path d="{d}" fill="{PANEL}" stroke="{color}" stroke-width="{f(width)}" '
        f'stroke-linejoin="miter"/>'
    )


def listing() -> str:
    """The root die, one rail, branches to folders and files, on a 512 field."""
    out = []
    rx = 176
    out.append(line([(rx, 118), (rx, 318)], GOLD, 6))
    for y, kind in ((150, "dir"), (204, "file"), (258, "dir"), (318, "file")):
        out.append(line([(rx, y), (rx + 52, y)], GOLD, 6))
        if kind == "dir":
            out.append(folder(rx + 54, y - 18, 64, 36, GOLD, 4))
            # The folder's own entry, one level down.
            sx = rx + 86
            out.append(line([(sx, y + 18), (sx, y + 34), (sx + 120, y + 34)], COPPER, 4))
            out.append(pad(sx + 126, y + 34, 8, COPPER))
            out.append(line([(rx + 118, y), (rx + 200, y)], COPPER, 4))
        else:
            out.append(node(rx + 66, y, 12))
            out.append(line([(rx + 78, y), (rx + 200, y)], COPPER, 3))
        out.append(via(rx + 206, y, 7, COPPER))
    out.append(die(rx, 96, 46, SILK))
    return "".join(out)


def listing_small() -> str:
    """The listing reduced for 64 px and below: root, rail, a folder, two files."""
    out = [line([(14, 18), (14, 52)], GOLD, 3)]
    for y, kind in ((28, "dir"), (42, "file"), (52, "file")):
        out.append(line([(14, y), (24, y)], GOLD, 3))
        out.append(folder(25, y - 6, 22, 12, GOLD, 2.2) if kind == "dir" else pad(28, y, 3.6, GOLD))
    out.append(die(14, 12, 12, GOLD))
    return "".join(out)


def frame(w: float, h: float, inset: float, c: float, heavy: float) -> str:
    """Double frame with 45-degree corners and a green diamond at each corner.

    :param w: Canvas width.
    :param h: Canvas height.
    :param inset: Distance of the heavy line from the canvas edge.
    :param c: Corner cut of the heavy line.
    :param heavy: Stroke width of the heavy line.
    """
    out = [
        f'<path d="{clipped_rect(inset, inset, w - 2 * inset, h - 2 * inset, c)}" fill="none" stroke="{GOLD}" stroke-width="{f(heavy)}"/>',
        f'<path d="{clipped_rect(inset * 1.9, inset * 1.9, w - 3.8 * inset, h - 3.8 * inset, c * 0.75)}" fill="none" stroke="{GOLD}" stroke-width="{f(heavy * 0.4)}" stroke-opacity=".6"/>',
    ]
    d = inset * 1.45 + c * 0.4375
    for cx, cy in ((d, d), (w - d, d), (d, h - d), (w - d, h - d)):
        out.append(diamond(cx, cy, inset * 0.5, GREEN))
    return "".join(out)


def svg(w: int, h: int, title: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f"<title>{title}</title>"
        f'<rect width="{w}" height="{h}" fill="{OBSIDIAN}"/>{body}</svg>\n'
    )


def mark(display, mono) -> str:
    """512 square mark: the listing, the name and the part line beneath."""
    body = frame(512, 512, 10, 26, 5) + listing()
    body += display.path(NAME, 256, 430, 40, 0.2, "middle", GOLD)
    body += mono.path(PART, 256, 462, 13.5, 0.3, "middle", MINT)
    return svg(512, 512, "FTreeKG mark, Art Techno", body)


def icon() -> str:
    """64 icon: the reduced listing in one heavy frame, no lettering."""
    body = f'<path d="{clipped_rect(2.5, 2.5, 59, 59, 7.5)}" fill="none" stroke="{GOLD}" stroke-width="3"/>'
    return svg(64, 64, "FTreeKG icon, Art Techno", body + listing_small())


def banner(display, mono) -> str:
    """1280 x 320 banner: the listing left, the name and part line right.

    The name is set as large as the room right of the listing allows, and the
    pair is centered on the banner's height.
    """
    s = 0.78
    body = frame(1280, 320, 10, 18, 3)
    body += f'<g transform="translate({f(230 - 256 * s)} {f(160 - 210 * s)}) scale({s})">{listing()}</g>'
    cx, room, gap = 820, 760, 34
    size = min(120, 120 * room / display.width(NAME, 120, 0.2))
    part = min(26, 26 * room / mono.width(PART, 26, 0.3))
    cap = display.cap * size / display.upm
    pcap = mono.cap * part / mono.upm
    base = (320 - (cap + gap + pcap)) / 2 + cap
    body += display.path(NAME, cx, base, size, 0.2, "middle", GOLD)
    body += mono.path(PART, cx, base + gap + pcap, part, 0.3, "middle", MINT)
    return svg(1280, 320, "FTreeKG banner, Art Techno", body)


def render(src: Path, out: Path, w: int, h: int) -> None:
    """Render the SVG ``src`` to ``out`` at ``w`` x ``h`` px with headless Chrome.

    :param src: SVG file; its ``width`` attribute sets the CSS width.
    :param out: PNG to write.
    :param w: Output width in px.
    :param h: Output height in px.
    """
    svg_w = int(src.read_text().split('width="', 1)[1].split('"', 1)[0])
    subprocess.run(
        [
            at.CHROME,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={svg_w},{svg_w * h // w}",
            f"--force-device-scale-factor={w / svg_w}",
            f"--screenshot={out}",
            src.as_uri(),
        ],
        check=True,
        capture_output=True,
    )


def main() -> None:
    at.fetch_fonts()
    display = at.Face(at.CACHE / "JosefinSans.ttf", weight=600)
    mono = at.Face(at.CACHE / "IBMPlexMono-Medium.ttf")

    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    mark_svg = assets / "ftreekg_logo.svg"
    icon_svg = assets / "ftreekg_icon.svg"
    banner_svg = assets / "ftreekg_banner.svg"
    mark_svg.write_text(mark(display, mono))
    icon_svg.write_text(icon())
    banner_svg.write_text(banner(display, mono))

    render(mark_svg, mark_svg.with_suffix(".png"), 1024, 1024)
    render(banner_svg, banner_svg.with_suffix(".png"), 2560, 640)


if __name__ == "__main__":
    main()
