# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **Claude Code plugin** (which doubles as its own single-plugin marketplace) containing the **`huawei-html-ppt`** skill: generating Huawei-official-template-style technical report slides as self-contained HTML (1280×720, 16:9), convertible to natively-editable PPTX. All content is in Chinese — keep it that way. There is no build/lint/test infrastructure; verification is visual (headless-Chrome screenshots, per-page cropping).

Layout: the skill lives at `skills/huawei-html-ppt/`; `.claude-plugin/plugin.json` + `marketplace.json` make the repo installable via `/plugin marketplace add LookAround0301/huawei-html-ppt` then `/plugin install huawei-html-ppt@huawei-html-ppt`. `.mcp.json` at the root auto-registers the bundled draw.io MCP server for plugin users.

## Skill architecture

`skills/huawei-html-ppt/SKILL.md` is the entrypoint and routes every task to a branch, each backed by a mandatory reference doc:

- **Branch A** — regular tech report pages: main flow in SKILL.md + `references/style-guide.md` (colors/fonts/layout/writing style).
- **Branch B** — PDCP/TDR project review (xlsx + reference PPTX): `references/pdcp-workflow.md` (style copied verbatim from reference materials, standard page sequence).
- **Branch C** — team "four maps" (业务/组织/人才/氛围): `references/four-maps-workflow.md`, data-driven via `tools/four-maps/`.
- **PPTX conversion** (only when explicitly requested, branches A/B): `references/pptx-conversion.md`.
- **Diagrams** (architecture/flow/topology): `references/drawio-diagram.md`, using the bundled offline draw.io server.

Supporting pieces:

- `assets/huawei.css` — the entire design system (CSS tokens + components). `assets/example.html` is a runnable example of every page type (cover/toc/summary/content/end).
- `tools/four-maps/` — `spec.yaml`-driven pipeline: `render_html.py` (HTML for user acceptance) and `generate.py` (native PPTX by cloning the official `assets/template.pptx`). `spec_example.yaml` is a fully validated example. All asset paths resolve relative to the script's own directory, so the tree is relocatable.
- `tools/drawio-server/` — bundled offline draw.io MCP server (`dist/index.js`, `node_modules` committed on purpose for offline use — ~37MB, don't prune). `tools/drive_drawio.mjs` drives it over stdio JSON-RPC when no MCP tools are registered in the session.

### Single-source-of-truth chains (do not break)

- Four-maps: **spec.yaml → HTML (acceptance) and PPTX (delivery)**. Change content only in spec, re-render both; never edit the two outputs independently.
- PPTX conversion (A/B): **delivered HTML → PPTX**. Data is parsed from the HTML (`<!-- ==== 页名 ==== -->` comment blocks); re-run the build script after HTML changes. Keep the `_build_pptx.py` script with the project.
- Design fixes go into `assets/huawei.css` tokens/components — not one-off styles in generated decks — so conventions sediment back into the design system.

## Commands

All skill paths below are relative to `skills/huawei-html-ppt/` (inside a plugin install this is a cache dir — docs use the `${CLAUDE_SKILL_DIR}` placeholder, which Claude Code substitutes at skill load time).

```bash
# Four-maps: render HTML for acceptance (--out MUST be absolute; --slide N renders one page for self-check)
python skills/huawei-html-ppt/tools/four-maps/render_html.py --spec spec.yaml --out "/abs/组名四张地图.html"

# Four-maps: native PPTX via template cloning (COM relayout needs Windows + PowerPoint; --no-relayout to skip)
python skills/huawei-html-ppt/tools/four-maps/generate.py --spec spec.yaml \
  --template skills/huawei-html-ppt/tools/four-maps/assets/template.pptx --out "/abs/组名四张地图.pptx"
python skills/huawei-html-ppt/tools/four-maps/export_png.py "组名四张地图.pptx" <preview-dir>   # Windows COM

# draw.io live preview (port defaults to 6002; set PORT env if occupied)
node skills/huawei-html-ppt/tools/drive_drawio.mjs diagram.drawio

# Plugin structure validation / local plugin testing
claude plugin validate ./
claude --plugin-dir ./        # then /reload-plugins after edits
```

Slide verification recipe (used after every deck change):

```
chrome --headless --disable-gpu --screenshot=_all.png --window-size=1312,<pages*736+pad> --hide-scrollbars "file:///<url-encoded path>"
```

Page pitch in the screenshot is **736px** (720 + collapsed 16px margin); page i (0-based) starts at `16 + i*736` — crop with PIL and inspect each page. Window width must be 1280 (= canvas width) or the body background bleeds into the sides.

Dependencies: python-pptx, pyyaml, pywin32 (COM), Pillow; Node for drawio-server. Note the drawio-server runtime and PNG/COM export steps were built for a Windows environment; on this Linux machine the HTML paths and `render_html.py` work, COM-based steps do not.

## Plugin maintenance notes

- **No `version` in plugin.json** — intentional: git-backed sources then version by commit SHA, so every push is an update for users (`/plugin update`). If you ever add a `version`, you must bump it on every change or users get stale copies.
- **This CLAUDE.md is repo-maintainer context only** — plugins do NOT load a root CLAUDE.md (`claude plugin validate` warns about it; that warning is expected and fine here).
- Path conventions: `${CLAUDE_PLUGIN_ROOT}` (plugin install dir) in `.mcp.json`/hooks; `${CLAUDE_SKILL_DIR}` (skill dir) inside SKILL.md and references. They are substituted at load time in skill content — reference files read later via the Read tool show the raw placeholder, so always phrase such paths as "relative to the skill root".
- `.mcp.json` registers the drawio server with `"command": "node"` — plugin users need Node on PATH; the server starts automatically in sessions where the plugin is enabled.
- When renaming anything: plugin name / marketplace name / skill name must stay consistent across `plugin.json`, `marketplace.json`, and `skills/<name>/`.

## Non-negotiable rules encoded in the skill docs

These come from real user feedback and incidents; treat the reference docs as prescriptive and don't casually rewrite their rules:

- **Color discipline**: only the 6-color template chart palette (`#C5C5C5 #929292 #666666 #E9002F #C00000 #FBA000`) + black/white/gray neutrals. No blues/greens/cyans anywhere (old CSS variable names like `--hw-blue` remain only as aliases).
- **Deliverables are single-file HTML**: CSS inlined into `<style>`, images base64-embedded. Dev iteration may `<link>` the skill's `huawei.css`, but decks still linking an old copy must be repacked after the skill CSS changes.
- **PPTX must be native editable objects** (text boxes/tables/shapes via python-pptx); full-page screenshot pasting is forbidden.
- Page footers `Page X/Y` are globally unique — renumber the whole deck after any insert/delete/split.
- "Conclusion-first" layout: judgment/summary elements (label blocks, KPI strips) go directly under the title with ≥20px gap; footers carry only source/calibration notes.
- Known pitfalls ("已踩过的坑") in `references/*.md` are documented real failures (GBK console → write UTF-8 dump files then Read; PowerPoint COM fails on non-ASCII paths; coordinate conversion done exactly once; `min-height:0` on cards containing SVG; headless Chrome cannot screenshot the draw.io preview page). Check these lists before troubleshooting from scratch.
