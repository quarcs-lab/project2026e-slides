"""Interactive (Plotly) twins of the deck's data charts — shared styling and output.

Interactive on the slides: the charts fig-ntl-sdg1-scatter, fig-r2-master (both schemes) and
fig-combined-range, and the cluster maps fig-views-lisa-{sdg1,sdg7,sdg13}. Each script still writes
its static SVG/PNG (the fallback, and what Tier B's palette-drift check reads) and ALSO calls
`write()` here, which emits `figures/<name>.html`: an
HTML FRAGMENT — one <div> and one inline <script> — that the .qmd pulls in with

    ```{=html}
    {{< include figures/<name>.html >}}
    ```

WHY A FRAGMENT AND NOT AN IFRAME. `embed-resources: true` makes the deck one self-contained file.
A fragment is plain slide content, so it inherits the deck's @font-face (Inter), needs no second
document, and is scaled by reveal.js together with the rest of the slide.

WHY THE NUMBERS LIVE IN THE FRAGMENT, NOT THE .qmd. Tier S scans the .qmd text and is fail-closed on
any undeclared number. The include shortcode keeps the chart data out of that text, exactly as an
<img> kept it inside an SVG.

THE LIBRARY. `write_library()` copies the plotly.js bundle that ships inside the pinned `plotly`
Python package to `figures/plotly.min.js`; `plotly.html` loads it from the head and Quarto inlines it.
No CDN: the deck must still work offline. The version therefore moves only with `uv.lock`.

FIXED PIXEL SIZE, NO AUTOSIZE, NO AUTOMARGIN. Reveal lays out a fixed 1280x720 canvas and scales it
as a whole, so a chart sized in logical pixels is the right unit (same reasoning as the px image
caps in theme.scss). Autosize would measure a hidden slide as 0x0, and automargin measures text
before the webfont has loaded, so both are off and the margins are set by hand.
"""
from __future__ import annotations

import html
import json

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs, get_plotlyjs_version

import _paths
from _palette import DECK

# NATIVE design size. Every figure is DESIGNED at this scale (460 px tall, the old 64vh image cap)
# and then enlarged as a whole by a per-figure factor S (see fit()), so text, markers and lines keep
# the proportions they were tuned at. A figure passes its own native width.
HEIGHT = 460
WIDTH = 1120
FONT = "Inter, 'Helvetica Neue', Arial, sans-serif"
TICK = 16
TITLE = 19
HOVER = 15

# The room a figure may fill, in the slide's logical 1280 x 720 coordinates. Measured, not guessed:
#   title ends at y = 52 (one line) or 104 (two lines); the figure starts 25 px below it;
#   below the figure: 4 px gap (theme.scss, section:has(.plotly-figure)), the 23 px source line,
#   then a 24 px bottom margin  ->  the figure must end by 720 - 24 - 23 - 4 = 669.
#   Width: the title's accent bar and the source line both start at x = 0, so the full 1280.
BOX_ONE_LINE = (1280, 669 - 77)       # 1280 x 592
BOX_TWO_LINE = (1280, 669 - 129)      # 1280 x 540


def fit(width: float, height: float, box: tuple[int, int]) -> float:
    """Largest uniform enlargement of a width x height design that fits `box` (proportions kept)."""
    return min(box[0] / width, box[1] / height)

# Presentation config: no floating toolbar over the slide, no scroll-zoom (the wheel would fight
# reveal's navigation), double-click resets a zoom. Hover and legend-click toggles stay on.
CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": "reset",
          "responsive": False, "showTips": False}


def axis(scale: float = 1.0, **kw) -> dict:
    base = dict(showgrid=False, zeroline=False, showline=True, linecolor=DECK["hairline"],
                linewidth=scale, ticks="outside", tickcolor=DECK["hairline"], ticklen=5 * scale,
                tickfont=dict(size=TICK * scale, color=DECK["ink"]),
                title=dict(font=dict(size=TITLE * scale, color=DECK["ink"]), standoff=10 * scale),
                fixedrange=True,
                # "y unified" hover draws a row spike; plotly's default is a loud white dotted rule.
                spikecolor=DECK["hairline"], spikethickness=scale, spikedash="solid")
    base["title"].update(kw.pop("title", {}))      # merge, so a caller's text keeps the standoff
    base.update(kw)
    return base


def layout(scale: float = 1.0, width: float = WIDTH, height: float = HEIGHT, **kw) -> dict:
    """Transparent, palette-only base layout, `width` x `height` native px enlarged by `scale`.
    Transparent for the same reason the SVGs are: the slide background is a gradient."""
    base = dict(
        width=round(width * scale), height=round(height * scale), autosize=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=TICK * scale, color=DECK["ink"]),
        hoverlabel=dict(bgcolor=DECK["bg_alt"], bordercolor=DECK["hairline"],
                        font=dict(family=FONT, size=HOVER * scale, color=DECK["ink"])),
        legend=dict(font=dict(size=15 * scale, color=DECK["ink"]), bgcolor="rgba(0,0,0,0)"),
        dragmode=False,
    )
    base.update(kw)
    return base


def write_library() -> None:
    """figures/plotly.min.js, rewritten only when the bundled version changes."""
    out = _paths.figure("plotly.min.js")
    js = get_plotlyjs()
    if not out.exists() or out.read_text(encoding="utf-8") != js:
        out.write_text(js, encoding="utf-8")


def write_geometry(g, outline) -> None:
    """figures/geo-municipalities.js — the 339 municipal polygons and the national outline, ONCE.

    Every map panel on every map slide draws the same polygons; only the class per municipality
    changes. So the geometry is a separate script (loaded by plotly.html) that defines
    `window.DECK_GEO` and `window.DECK_OUTLINE`, and `write()` attaches it to the traces in the
    browser. Inlining it per trace would multiply ~0.3 MB by the number of panels.

    NOT SIMPLIFIED, only rounded to 3 decimals (~110 m, below a pixel at slide scale). The source
    file is already simplified upstream: coverage simplification removes almost nothing until
    ~2 km, and at 2 km the smallest municipalities (Nazacara de Pacajes, Tito Yupanqui, ~16-18 km²)
    lose up to 18% of their area. That trade is not worth ~150 KB. Display only — the weights and
    LISA classes are always computed on the unrounded file (_fourview.geo).

    `g` is EPSG:4326 with `asdf_id`; `outline` is the dissolved national boundary (a line geometry).
    """
    import numpy as np
    import shapely

    def rounded(geom):
        return json.loads(shapely.to_geojson(shapely.transform(geom, lambda c: np.round(c, 3))))

    fc = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": int(i), "properties": {}, "geometry": rounded(geom)}
        for i, geom in zip(g["asdf_id"], g.geometry)]}
    lon, lat = [], []
    for line in getattr(outline, "geoms", [outline]):
        for x, y in np.round(np.asarray(line.coords), 3):
            lon.append(float(x))
            lat.append(float(y))
        lon.append(None)
        lat.append(None)
    js = (f"/* GENERATED by scripts/_interactive.py write_geometry() — do not hand-edit */\n"
          f"window.DECK_GEO={json.dumps(fc, separators=(',', ':'))};\n"
          f"window.DECK_OUTLINE={json.dumps({'lon': lon, 'lat': lat}, separators=(',', ':'))};\n")
    out = _paths.figure("geo-municipalities.js")
    if not out.exists() or out.read_text(encoding="utf-8") != js:
        out.write_text(js, encoding="utf-8")


# Draw only when the slide is shown (or in print view). Map fragments use this: three slides of
# four-panel maps drawn at page load would delay the whole deck for slides nobody has reached.
_LAZY = (
    'function arm(){{var sec=document.getElementById(id).closest("section");'
    'function maybe(){{if(Reveal.getCurrentSlide()===sec||(Reveal.isPrintView&&Reveal.isPrintView()))draw();}}'
    'Reveal.on("ready",maybe);Reveal.on("slidechanged",maybe);if(Reveal.isReady&&Reveal.isReady())maybe();}}'
    # Decide AFTER parsing: Quarto loads reveal.js at the end of <body>, i.e. after this fragment, so
    # testing window.Reveal inline is always false and would draw every map at page load.
    'document.addEventListener("DOMContentLoaded",function(){{if(window.Reveal)arm();else draw();}});'
)


def write(fig: go.Figure, name: str, alt: str, script: str, *, config: dict | None = None,
          lazy: bool = False, post: str = "") -> None:
    """figures/<name>.html — one <div> plus the script that draws into it.

    Traces with `meta="geo"` (choropleths) get `window.DECK_GEO` as their geojson, and traces
    with `meta="outline"` get the national outline, in the browser — see `write_geometry()`.
    `post` is JavaScript run once the plot exists, with the plot element bound to `gd`.
    """
    write_library()
    spec = json.loads(fig.to_json())      # plotly's encoder handles numpy/pandas types
    # Drop plotly's default template: it is ~10 KB per chart and carries colours outside the palette.
    spec["layout"].pop("template", None)
    payload = json.dumps({"data": spec["data"], "layout": spec["layout"],
                          "config": {**CONFIG, **(config or {})}},
                         separators=(",", ":"), ensure_ascii=False)
    payload = payload.replace("</", "<\\/")   # hover templates carry </b>; never close the <script>
    draw = (
        "var drawn=false;function draw(){if(drawn)return;drawn=true;"
        's.data.forEach(function(t){if(t.meta==="geo")t.geojson=window.DECK_GEO;'
        'if(t.meta==="outline"){t.lon=window.DECK_OUTLINE.lon;t.lat=window.DECK_OUTLINE.lat;}});'
        f"Plotly.newPlot(id,s.data,s.layout,s.config).then(function(gd){{{post}}});}}"
    )
    fragment = (
        f"<!-- GENERATED by scripts/{script} via _interactive.py "
        f"(plotly.js {get_plotlyjs_version()}) — do not hand-edit -->\n"
        f'<div id="{name}" class="plotly-figure" role="img" aria-label="{html.escape(alt, quote=True)}" '
        f'style="width:{spec["layout"]["width"]}px;height:{spec["layout"]["height"]}px;'
        f'margin:0 auto;"></div>\n'
        f'<script>(function(){{var id="{name}";var s={payload};{draw}'
        f'{_LAZY.format() if lazy else "draw();"}}})();</script>\n'
    )
    out = _paths.figure(f"{name}.html")
    out.write_text(fragment, encoding="utf-8")
