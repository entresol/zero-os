#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Builds the GitHub Pages landing page (index.html) for the zOS paper. No author names."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

src_dir = Path(sys.argv[1])   # folder with src.md, fig1.png, fig2.png, stations.json, paper.pdf
out = Path(sys.argv[2])       # site output folder
pdf_name = "zos-zero-os.pdf"

md = (src_dir / "src.md").read_text(encoding="utf-8")
lines = md.splitlines()
body = "\n".join(lines[4:]).split("\n", 1)[1]      # drop title, subtitle, date/author line

# the prologue's first two paragraphs become the hero; remove them from the body
pro = re.search(r"## Prologue: Imagine it's 1991\n\nImagine it's 1991\. We are about to release a few lines of code into a world that will be very different from today\.\n\n", body)
body = body[:pro.start()] + "## Prologue: Imagine it's 1991\n\n" + body[pro.end():]

import json, html as _h
cap1 = "Figure 1. The zOS stack. A gold frame marks the trusted base: every part a guarantee depends on, isolated or not. The tag says what we know about it. Authority runs from the agent through the broker, motion through the safety controller; there is no third path."
alt1 = ("Diagram of the zOS stack. Top: agents (untrusted, outside the trusted base) send authority requests to the capability broker "
        "(isolated but in the trusted base, tested, target proven), which alone reaches tools and model access (outside the base). "
        "Agents send motion proposals to the safety controller and control loops (trusted base, tested, target proven), which alone move the actuator. "
        "Below: user-mode drivers and the Linux driver island (outside the base where the IOMMU confines the device), the static system description (trusted, tested), "
        "the seL4 microkernel with MCS (trusted, proven for its verified configurations), the bootloader (trusted, assumed) and firmware, hardware and root of trust (trusted, assumed).")
fig1 = (f'<figure class="wide"><div class="fig-scroll"><img src="assets/fig1.png" alt="{_h.escape(alt1)}" width="1344" loading="lazy"></div>'
        f'<figcaption>{cap1}</figcaption></figure>')
body = re.sub(r"&#91;embedded content: Fig\. 1[^\n]*", "\n```{=html}\n" + fig1 + "\n```\n", body)

stations = json.loads((src_dir / "stations.json").read_text(encoding="utf-8"))
kinds = {"DEMO": "Demonstration", "TEST": "Test", "PROOF": "Proof"}
items = []
for yr, name, sub, kind, check in stations:
    badge = f'<span class="kind">{kinds[kind]}</span> ' if kind else ""
    cls = ' class="start"' if not kind else ""
    items.append(f'<li{cls}><span class="year">{yr}</span><div><p class="st-name">{_h.escape(name)}</p>'
                 f'<p class="st-sub">{_h.escape(sub)}</p><p class="st-check">{badge}{_h.escape(check)}</p></div></li>')
cap2 = "Figure 2. The path from 2026 to 2031, read from the bottom up. Each station names its evidence and whether it is a demonstration, a test or a proof; a failed check stops the path."
fig2 = (f'<figure class="timeline"><ol>{"".join(items)}</ol><figcaption>{cap2}</figcaption></figure>')
body = re.sub(r"&#91;embedded content: Fig\. 2[^\n]*", "\n```{=html}\n" + fig2 + "\n```\n", body)

body = body.replace("Table 1 lists them", "The table lists them")
html_body = subprocess.run(
    ["pandoc", "-f", "markdown", "-t", "html5", "--wrap=none"],
    input=body, capture_output=True, text=True, check=True).stdout

# external links open in a new tab; tables get a wrapper for horizontal scroll on phones
html_body = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" rel="noopener" target="_blank"', html_body)
html_body = html_body.replace("<table>", '<div class="table-wrap wide"><table>').replace("</table>", "</table></div>")

# references get ids; in-text citations link to them
ref_part = html_body.split('<h2 id="references">', 1)
refs_html = ref_part[1]
cites = {}
def cite_key(li_text):
    m = re.match(r"\s*(.+?) \((?:eds\.\) \()?((?:\d{4}|n\.d\.)[a-z]?(?:-[a-z])?)\)", li_text)
    if not m:
        return None
    who, year = m.group(1), m.group(2)
    who = re.sub(r"\s*\(eds\.\)", "", who)
    if " et al." in who:
        names = who.split(",")[0] + " et al."
    elif ";" in who:
        parts = [p.strip().split(",")[0] for p in who.split(";")]
        names = parts[0] + " and " + parts[1] if len(parts) == 2 else parts[0] + " et al."
    elif re.match(r"^[^,]+, [A-Z]\.", who):
        names = who.split(",")[0]
    else:
        names = who
    return f"{names} {year}"
n = 0
def add_id(m):
    global n
    n += 1
    txt = re.sub("<[^>]+>", "", m.group(1)).replace("\xa0", " ")
    k = cite_key(txt)
    rid = f"ref-{n}"
    if k:
        cites[k] = rid
    return f'<li id="{rid}">{m.group(1)}</li>'
refs_html = re.sub(r"<li>(.*?)</li>", add_id, refs_html, flags=re.S)
main_html = ref_part[0]
keys = sorted(cites, key=len, reverse=True)
pat = re.compile("|".join(re.escape(k).replace(r"\ ", "[ \xa0]") for k in keys))
def link_text(chunk):
    return pat.sub(lambda m: f'<a class="cite" href="#{cites[m.group(0).replace(chr(160), " ")]}">{m.group(0)}</a>', chunk)
# only touch text outside tags and outside existing links
segs = re.split(r"(<a\b.*?</a>|<[^>]+>)", main_html, flags=re.S)
main_html = "".join(seg if seg.startswith("<") else link_text(seg) for seg in segs)
html_body = main_html + '<h2 id="references">' + refs_html
n_refs = n
unlinked = sorted(set(re.findall(r"\(([A-Z][^()]*?\d{4}[a-z]?)\)", re.sub(r"<a\b.*?</a>", "", main_html).replace("\xa0", " "))))
if unlinked:
    print("check citations:", unlinked[:12])

def label_table(m):
    t = m.group(0)
    heads = [re.sub("<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", t, flags=re.S)]
    def lab_row(r):
        cells = iter(heads)
        return re.sub(r"<td([^>]*)>", lambda c: f'<td{c.group(1)} data-label="{next(cells, "")}">', r.group(0))
    return re.sub(r"<tr.*?</tr>", lab_row, t, flags=re.S)
html_body = re.sub(r"<table>.*?</table>", label_table, html_body, flags=re.S)

# revisions: what changed between versions, each with the PDF as it was
REPO = "https://github.com/entresol/zero-os"
revisions = [
    ("2026-10-23-v0.8", None,
     "The name is marked as a working title. Section 1 opens with the motivation for everything else: Don't trust the agent. Verify the system. The agent is treated as a Byzantine component; the size of the system follows from the reference monitor's oldest requirement, to be small enough to be analysed and tested."),
    ("2026-10-23-v0.7", "2a9d5b7",
     "The abstract states the thesis up front: zOS does not try to make AI trustworthy, it stays safe although the agent is not. Section 5 adds AgenticOS and Agent libOS as designs for the broker's job and the first verified LionsOS driver. He et al. cited in its OSDI '26 version."),
    ("2026-10-23-v0.6", "0459cdc",
     "Text and figures are licensed under CC BY 4.0."),
    ("2026-10-20-v0.5", "79e70978704a9c21803560dc46ba265951966250",
     "The bootloader paragraph says what the first prototype does: one fixed rule; the first screen drawn by the loader, because nothing else could report a failed check; its size counted as trusted base."),
    ("2026-10-20-v0.4", "5cb6f1350b744973727f9aa11a979f8f6432d35b",
     "The slogan becomes the subtitle: Bare minimum. Verified. Real-time. An OS for the AI era. The authors are named on the paper."),
    ("2026-10-20-v0.3", "4e2feba",
     "pib as a possible first robot. The driver island, the seams on critical paths and the dependency on seL4 dates made explicit. Anthropic's vulnerability figures qualified as self-reported."),
    ("2026-10-20-v0.2", "93d142bdf3b51c831caf5c16bf23b34040fb6ea4",
     "Revision after the first external review: a first use case; two questions per part instead of three trust classes; firmware above the kernel; what has to be built and who else is building it; the hardened-Linux alternative; reviews described as AI-assisted; every roadmap station labelled demonstration, test or proof. New figures."),
    ("2026-10-19-v0.1", "adf2d5d308735e0408c63341b3cc01b49d1f7a15", "First publication."),
]
rev_items = []
for ver, sha, text in revisions:
    pdf = f'<a href="versions/zos-zero-os-{ver}.pdf">PDF of this version</a>'
    rev_items.append(f'<li><p class="rev-date"><span class="rev-ver">{ver}</span> · {pdf}</p><p>{text}</p></li>')
revisions_html = ('<h2 id="revisions">Revisions</h2>'
                  f'<p>Every change is recorded in the <a href="{REPO}/commits/main">commit history</a>. '
                  'This list says what changed in substance.</p>'
                  f'<ol class="revisions">{"".join(rev_items)}</ol>')
html_body = html_body + revisions_html
CURRENT_VERSION = revisions[0][0]
pdf_name = f"versions/zos-zero-os-{CURRENT_VERSION}.pdf"

# table of contents from h2
toc = "".join(f'<li><a href="#{i}">{re.sub("<[^>]+>", "", t)}</a></li>'
              for i, t in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', html_body))

pages = subprocess.run(["pdfinfo", str(src_dir / "paper.pdf")], capture_output=True, text=True).stdout
pages = re.search(r"Pages:\s+(\d+)", pages).group(1)
css = (Path(__file__).resolve().parent / "site.css").read_text(encoding="utf-8")
css = "\n".join(l for l in css.splitlines() if "SPDX-License-Identifier" not in l) + "\n"
page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>zOS – Zero OS</title>
<meta name="description" content="zOS – Bare minimum. Verified. Real-time. An OS for the AI era. A working paper: a bootloader, a formally verified microkernel and the bare minimum to run AI safely and in real time, built entirely from existing open source.">
<link rel="preload" href="assets/fonts/inter-latin-opsz-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/fonts/nunito-sans-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<style>
{css}
</style>
</head>
<body>
<header class="hero">
  <div class="hero-inner">
    <h1>Imagine it's 1991</h1>
    <p class="lede">We are about to release a few lines of code into a world that will be very different from today.</p>
    <div class="titleblock">
      <p class="name">zOS – Zero OS<a class="star" href="#working-title" aria-label="About the name">*</a></p>
      <p class="sub">Bare minimum. Verified. Real-time. An OS for the AI era.</p>
      <p class="ver">Working paper {CURRENT_VERSION} · <a href="#revisions">latest changes</a></p>
    </div>
    <p class="status">First light: <a href="https://github.com/entresol/zero-os/tree/main/loader">a loader that checks the kernel image and shows its verdict on the first screen</a>, under 9 KB on RISC-V, tested in QEMU. This paper proposes what we intend to build and where it can fail. Criticism and support are warmly welcome: <a href="https://github.com/entresol/zero-os/issues">issues</a>.</p>
    <div class="actions">
      <a class="btn" href="{pdf_name}">Download the PDF</a>
      <span class="meta">{pages} pages, {n_refs} references</span>
    </div>
  </div>
</header>
<div class="layout">
  <nav class="toc" aria-label="Contents"><p>Contents</p><ol>{toc}</ol></nav>
  <article>
{html_body}
  </article>
</div>
<footer><div><span>zOS – Zero OS. Working paper {CURRENT_VERSION}. <a href="https://github.com/entresol/zero-os">Source and discussion on GitHub</a>. Text and figures: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.</span><span id="working-title">* zOS is a working title. Before its first release the project gets a name of its own, one that treads on nobody's toes, mainframes included.</span><a href="{pdf_name}">Download the PDF</a></div></footer>
</body>
</html>
"""

out.mkdir(parents=True, exist_ok=True)
(out / "assets").mkdir(exist_ok=True)
(out / "index.html").write_text(page, encoding="utf-8")
fontdir = Path(__file__).resolve().parent.parent / "assets" / "fonts"   # self-hosted fonts, SIL OFL 1.1
(out / "assets" / "fonts").mkdir(exist_ok=True)
if (out / "assets" / "fonts").resolve() != fontdir.resolve():
    for f in list(fontdir.glob("*.woff2")) + list(fontdir.glob("LICENSE*")):
        shutil.copy(f, out / "assets" / "fonts" / f.name)
shutil.copy(src_dir / "fig1.png", out / "assets" / "fig1.png")
old_fig2 = out / "assets" / "fig2.png"
if old_fig2.exists():
    old_fig2.unlink()
(out / "versions").mkdir(exist_ok=True)
shutil.copy(src_dir / "paper.pdf", out / pdf_name)            # this version, named by its version
shutil.copy(src_dir / "paper.pdf", out / "zos-zero-os.pdf")    # stable name, always the newest version
(out / ".nojekyll").write_text("")
print("ok", len(page))
