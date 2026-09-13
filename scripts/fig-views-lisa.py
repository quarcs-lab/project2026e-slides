# Four views of the SPATIAL STRUCTURE of one goal: local indicators of spatial association,
# row-standardised QUEEN CONTIGUITY (code/spatial_weights.queen_repaired), p < 0.05, one panel
# per view. Every statistic printed below is asserted against the manuscript's own
# tables/tbl-views-comparison-<slug>.csv before the figure is written.
#
#   usage: fig-views-lisa.py [sdg1|sdg7|sdg13]      (default sdg1)
#
# All three indices score ACHIEVEMENT (higher = better), so the geometry of the legend is uniform:
#   high-high (red)  = a cluster of HIGH achievement
#   low-low  (blue)  = a cluster of LOW achievement — the trap
#   orange / light blue = spatial outliers (a place unlike its neighbours)
# The WORDING is not uniform and comes from FV.GOALS[slug]: "poverty trap" is meaningful to an
# audience and meaningless on the energy map.
#
# Prints each panel's global Moran's I and its agreement with the actual cluster map, which is
# what the slide's numbers are traced to.
#
# Reproduces figures/fig-views-lisa-<slug>.png
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

import _fourview as FV
from _palette import DECK, apply_deck_style

apply_deck_style()

SLUG = sys.argv[1] if len(sys.argv) > 1 else FV.DEFAULT_SLUG
GOAL = FV.GOALS[SLUG]
df = FV.load(SLUG)
g = FV.geo(df)                             # NATIVE CRS — the weights must match the manuscript's
w = FV.queen_weights(g)

labels, morans, local_i, p_sim = {}, {}, {}, {}
for col in FV.VIEW_COLS:
    labels[col], morans[col], local_i[col], p_sim[col] = FV.lisa(g[col].to_numpy(), w)

# Gate BEFORE plotting: a figure that disagrees with the paper should never reach the deck.
FV.verify_against_paper(SLUG, morans, labels)

gm = FV.web_mercator(g)                    # reproject only for display

# One row of four — see the layout note in fig-views-choropleth.py.
fig, axes = plt.subplots(1, 4, figsize=(15.0, 6.0))
for ax, col in zip(axes.ravel(), FV.VIEW_COLS):
    cl = pd.Series(labels[col])
    for cat in FV.PLOT_ORDER:                       # grey first, clusters on top
        sel = gm[(cl == cat).to_numpy()]
        if len(sel):
            sel.plot(ax=ax, color=FV.CLUSTER_COLORS[cat], edgecolor="white", linewidth=0.15)
    # THREE statistics per panel, not one. This used to print only the hot/coldspot share, and on
    # the poverty slide that single number read (c) embeddings 80% against (d) combined 75% — under
    # a title asserting the combined view recovers the geography best. The figure appeared to refute
    # its own slide, because the evidence that supports the title (agreement over the FULL
    # classification, and clustering strength) was only in the speaker notes. A geospatial audience
    # reads the panel headers. Caught by the 2026-07-28 rhetoric audit.
    if col == "actual":
        sub = f"reference · I = {morans[col]:.2f}"
    else:
        agree = float((pd.Series(labels[col]) == pd.Series(labels["actual"])).mean())
        sub = (f"{agree:.0%} of all clusters · {FV.hotcold_agreement(labels, col):.0%} of hot/cold"
               f"\nMoran's I {morans[col]:.2f}  (actual {morans['actual']:.2f})")
    ax.set_title(f"{FV.PANEL_TITLES[col]}\n{sub}",
                 fontsize=12.5, color=DECK["ink"], pad=8, linespacing=1.5)
    FV.outline(gm, ax)
    ax.set_axis_off()

handles = [Patch(facecolor=FV.CLUSTER_COLORS[c], edgecolor="white", label=lab) for c, lab in [
    ("High-high", GOAL["hi_label"]),
    ("Low-low", GOAL["lo_label"]),
    ("High-low", "Outlier: high among low"),
    ("Low-high", "Outlier: low among high"),
    ("Not significant", "Not significant"),
]]
fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=14,
           bbox_to_anchor=(0.5, -0.02))
fig.subplots_adjust(wspace=0.01, left=0.01, right=0.99, top=0.88, bottom=0.06)
out = DECKDIR / f"figures/fig-views-lisa-{SLUG}.png"
fig.savefig(out, dpi=192, bbox_inches="tight")

# Agreement with the actual cluster map: over all classes, and over hotspots/coldspots only.
actual = pd.Series(labels["actual"])
hotcold = actual.isin(["High-high", "Low-low"])
print("wrote", out.name)
print(f"  {'view':<28} {'Moran I':>8} {'all classes':>12} {'hot/coldspots':>14}")
print(f"  {'(a) Actual':<28} {morans['actual']:>8.2f} {'—':>12} {'—':>14}")
for col in FV.VIEW_TAGS:
    pred = pd.Series(labels[col])
    agree_all = float((pred == actual).mean())
    agree_hc = float((pred[hotcold] == actual[hotcold]).mean())
    print(f"  {FV.PANEL_TITLES[col]:<28} {morans[col]:>8.2f} "
          f"{agree_all:>11.0%} {agree_hc:>13.0%}")

# ---- interactive twin: figures/fig-views-lisa-<slug>.html (what the slides show, all three goals) -
# Same four panels, classes, colours, panel statistics and legend as the PNG, drawn as SVG
# choropleths (plotly `choropleth`, not the WebGL `choroplethmap`: four WebGL contexts per slide and
# no basemap to justify them). Everything above — weights, LISA, verify_against_paper() — is
# unchanged; this block only draws classes that have already passed the gate.
#
#   hover    one municipality: its name, and in ALL FOUR views its index value, class, local
#            Moran's I and pseudo p; it is outlined in every panel, so "did the prediction find
#            this cluster?" is one gesture;
#   zoom     mouse wheel zooms, drag pans; the four panels stay locked together; double-click resets.
#
# The polygons are not in this fragment: figures/geo-municipalities.js carries them once for every
# map slide (see _interactive.write_geometry). The fragment draws lazily, when its slide is shown.
import plotly.graph_objects as go        # noqa: E402

import _interactive as I                 # noqa: E402
import labels as L                       # noqa: E402

I.write_geometry(g, g.dissolve().boundary.iloc[0])

CLASS_LABEL = {"High-high": GOAL["hi_label"], "Low-low": GOAL["lo_label"],
               "High-low": "Outlier: high among low", "Low-high": "Outlier: low among high",
               "Not significant": "Not significant"}
CODE = {c: k for k, c in enumerate(FV.PLOT_ORDER)}
names = pd.read_csv(_paths.data("regionNames/regionNames.csv"))[["asdf_id", "mun", "dep"]]
info = g[["asdf_id"]].merge(names, on="asdf_id", how="left", validate="one_to_one")
assert info["mun"].notna().all(), "a municipality has no name"
# Tooltip, identical in all four panels: name, what the index is, then per view two lines —
#   (x) View: <index value> — <class>
#       Local Moran's I = <Ii>, p = <pseudo p>
# The value is the series that view's LISA ran on; Ii and p come from that same run (FV.lisa), so
# the numbers and the class can never disagree. Per-view columns: value, class, Ii, p.
# Rows are plain Python lists, not a numpy string array, so the numbers stay numbers and plotly's
# :.1f/:.2f/:.3f formats apply.
custom = [
    [info["mun"].iat[i], info["dep"].iat[i]]
    + [x for col in FV.VIEW_COLS for x in (float(g[col].iat[i]), CLASS_LABEL[labels[col][i]],
                                           float(local_i[col][i]), float(p_sim[col][i]))]
    for i in range(len(g))
]
INDENT = "\u00a0" * 6                  # plotly collapses ordinary spaces in hover text
hover = (f"<b>%{{customdata[0]}}</b> · %{{customdata[1]}}<br>{L.GOAL_LABEL[GOAL['target']]} index, 2017"
         + "".join(
             f"<br>{FV.PANEL_TITLES[col]}: %{{customdata[{2 + 4 * k}]:.1f}} — %{{customdata[{3 + 4 * k}]}}"
             f"<br>{INDENT}Local Moran's I = %{{customdata[{4 + 4 * k}]:.2f}}, p = %{{customdata[{5 + 4 * k}]:.3f}}"
             for k, col in enumerate(FV.VIEW_COLS))
         + "<extra></extra>")

# Discrete colourscale: class k of 5 sits at k/4, each colour owns the band around it.
n = len(FV.PLOT_ORDER)
scale = []
for k, c in enumerate(FV.PLOT_ORDER):
    scale += [[max(0.0, (k - 0.5) / (n - 1)), FV.CLUSTER_COLORS[c]],
              [min(1.0, (k + 0.5) / (n - 1)), FV.CLUSTER_COLORS[c]]]

minx, miny, maxx, maxy = g.total_bounds
GAP, TOP, BOTTOM = 0.004, 0.85, 0.08
NATIVE_W = 1180                          # designed at 1180 x I.HEIGHT, enlarged uniformly by S
S = I.fit(NATIVE_W, I.HEIGHT, I.BOX_TWO_LINE)
ifig = go.Figure()
geo_layout = {}
for k, col in enumerate(FV.VIEW_COLS):
    gid = "geo" if k == 0 else f"geo{k + 1}"
    x0, x1 = k / 4 + GAP, (k + 1) / 4 - GAP
    geo_layout[gid] = dict(
        domain=dict(x=[x0, x1], y=[BOTTOM, TOP]), projection=dict(type="mercator"),
        lonaxis=dict(range=[minx - 0.05, maxx + 0.05]), lataxis=dict(range=[miny - 0.05, maxy + 0.05]),
        visible=False, showframe=False, bgcolor="rgba(0,0,0,0)")
    ifig.add_trace(go.Choropleth(
        geo=gid, meta="geo", featureidkey="id", locations=g["asdf_id"],
        z=[CODE[c] for c in labels[col]], zmin=0, zmax=n - 1, colorscale=scale, showscale=False,
        marker=dict(line=dict(color="rgba(238,243,249,0.28)", width=0.4 * S)),   # DECK["ink"], faint
        customdata=custom, hovertemplate=hover, name=FV.PANEL_TITLES[col],
        # left-aligned even when the label flips to the cursor's left (panels c-d): plotly would
        # otherwise right-align it and the indented second line of each view would stop reading as one.
        hoverlabel=dict(align="left"),
    ))
    ifig.add_trace(go.Scattergeo(geo=gid, meta="outline", lon=[], lat=[], mode="lines",
                                 line=dict(color=FV.OUTLINE, width=1.1 * S), hoverinfo="skip",
                                 showlegend=False))
    if col == "actual":
        sub = f"reference · I = {morans[col]:.2f}"
    else:
        agree = float((pd.Series(labels[col]) == pd.Series(labels["actual"])).mean())
        sub = (f"{agree:.0%} of all clusters · {FV.hotcold_agreement(labels, col):.0%} of hot/cold"
               f"<br>Moran's I {morans[col]:.2f}  (actual {morans['actual']:.2f})")
    ifig.add_annotation(
        x=(x0 + x1) / 2, y=1.0, xref="paper", yref="paper", xanchor="center", yanchor="top",
        showarrow=False, align="center",
        text=(f"<span style='font-size:{16 * S:.1f}px'>{FV.PANEL_TITLES[col]}</span><br>"
              f"<span style='font-size:{13 * S:.1f}px;color:{DECK['muted']}'>{sub}</span>"))

# Legend swatches: empty traces, one per class, in the PNG's legend order. Not clickable — hiding a
# swatch would hide nothing on the map and read as a broken control.
for c in FV.LEGEND_ORDER:
    ifig.add_trace(go.Scattergeo(geo="geo", lon=[None], lat=[None], mode="markers",
                                 name=CLASS_LABEL[c], hoverinfo="skip",
                                 marker=dict(symbol="square", size=15 * S, color=FV.CLUSTER_COLORS[c],
                                             line=dict(color="rgba(238,243,249,0.6)", width=S))))

ifig.update_layout(I.layout(
    S, width=NATIVE_W, margin=dict(l=0, r=0, t=0, b=0), dragmode="pan", hovermode="closest",
    legend=dict(orientation="h", x=0.5, y=0.02, xanchor="center", yanchor="bottom",
                font=dict(size=15 * S), itemclick=False, itemdoubleclick=False),
    **geo_layout,
))

# Linked highlight: a CSS class on the hovered municipality's path in every panel (no redraw), and
# locked zoom/pan: any panel's relayout is copied to the other three.
POST = f"""
var st=document.createElement("style");
st.textContent="#"+id+" path.choroplethlocation.hl{{stroke:{DECK['ink']}!important;stroke-width:{2.2 * S:.2f}px!important}}";
document.head.appendChild(st);
var off=null;
function mark(loc){{gd.querySelectorAll("path.choroplethlocation").forEach(function(p){{
  var on=p.__data__&&String(p.__data__.loc)===loc;
  p.classList.toggle("hl",on); if(on)p.parentNode.appendChild(p);}});}}
gd.on("plotly_hover",function(e){{var p=e.points&&e.points[0];if(!p||p.location===undefined)return;
  clearTimeout(off);mark(String(p.location));}});
gd.on("plotly_unhover",function(){{off=setTimeout(function(){{mark(null);}},120);}});
var geos=["geo","geo2","geo3","geo4"],busy=false;
gd.on("plotly_relayout",function(ev){{if(busy)return;var src=null;
  Object.keys(ev).forEach(function(k){{var m=k.match(/^(geo\\d?)\\./);if(m)src=m[1];}});
  if(!src)return;var f=gd._fullLayout[src],up={{}};
  geos.forEach(function(g){{if(g===src)return;up[g+".projection.scale"]=f.projection.scale;
    up[g+".center.lon"]=f.center.lon;up[g+".center.lat"]=f.center.lat;}});
  busy=true;Plotly.relayout(gd,up).then(function(){{busy=false;}},function(){{busy=false;}});}});
"""
I.write(ifig, f"fig-views-lisa-{SLUG}", script="fig-views-lisa.py", lazy=True, post=POST,
        config={"scrollZoom": True},
        alt=(f"Interactive four-panel map of local spatial clusters in {GOAL['label']} ({GOAL['theme']}) "
             "across Bolivia's 339 municipalities: actual, nighttime lights, daytime embeddings and "
             "combined predictions. Hover a municipality to see its class in every view; scroll to zoom."))
print(f"wrote fig-views-lisa-{SLUG}.html  (interactive)")
