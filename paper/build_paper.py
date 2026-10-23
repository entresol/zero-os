#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Turns src.md into paper.tex (two-column A4, pdfLaTeX). Run pdflatex twice on the result; build.sh does all of it."""
import re
import subprocess
import sys
from pathlib import Path

work = Path(sys.argv[1])  # folder with src.md, fig1.png, fig2.png
src = (work / "src.md").read_text(encoding="utf-8")

lines = src.splitlines()
title = lines[0].lstrip("# ").strip()
subtitle = lines[2].lstrip("# ").strip()
body = "\n".join(lines[4:]).split("\n", 1)[1]  # drop date/author line

abs_match = re.search(r"## Abstract\n(.*?)\n## Prologue", body, re.S)
abstract_md = abs_match.group(1).strip()
body = body[abs_match.end() - len("## Prologue"):]

kw_match = re.search(r"\*\*Keywords:\*\*\s*(.*)$", abstract_md, re.M)
keywords = kw_match.group(1).strip()
abstract_md = abstract_md[: kw_match.start()].strip()

# figure placeholders out, figure anchors one section earlier (figure* floats to next page top)
body = re.sub(r"&#91;embedded content: Fig\. 1[^\n]*\n", "", body)
body = re.sub(r"&#91;embedded content: Fig\. 2[^\n]*\n", "", body)
body = body.replace("## 3 Anatomy", "FIGUREONE\n\n## 3 Anatomy", 1)
body = body.replace("## 6 What zOS", "FIGURETWO\n\n## 6 What zOS", 1)


# component table -> full-width table* (longtable cannot live in two-column mode)
tbl = re.search(r"\n(\| Component.*?)\n\n", body, re.S)
rows = [r.strip().strip("|").split("|") for r in tbl.group(1).splitlines()]
rows = [[c.strip() for c in r] for r in rows if not set("".join(r)) <= set("- :")]

def esc(t):
    for a, b in [("\\", "\\textbackslash{}"), ("&", "\\&"), ("%", "\\%"), ("_", "\\_"), ("#", "\\#"), ("$", "\\$")]:
        t = t.replace(a, b)
    return t.replace("\u2013", "--")

hdr, data = rows[0], rows[1:]
lines_t = [" & ".join("\\textbf{%s}" % esc(c) for c in hdr) + " \\\\ \\midrule"]
lines_t += [" & ".join(esc(c) for c in r) + " \\\\" for r in data]
table_tex = ("\\begin{table*}[tb]\n\\centering\n\\footnotesize\n\\renewcommand{\\arraystretch}{1.25}\n"
             "\\begin{tabularx}{\\textwidth}{@{}>{\\raggedright\\arraybackslash}p{2.9cm}>{\\raggedright\\arraybackslash}p{3.6cm}>{\\raggedright\\arraybackslash}X@{}}\n\\toprule\n" + "\n".join(lines_t) +
             "\n\\bottomrule\n\\end{tabularx}\n\\caption{Nothing to invent: the open-source parts of zOS and their state in 2026.}\n\\end{table*}")
body = body.replace(tbl.group(1), "TABLEONE")
body = body.replace("## 5 Nothing to invent", "## 5 Nothing to invent", 1)

def pandoc(md: str) -> str:
    return subprocess.run(
        ["pandoc", "-f", "markdown-auto_identifiers", "-t", "latex",
         "--shift-heading-level-by=-1", "--wrap=preserve"],
        input=md, capture_output=True, text=True, check=True,
    ).stdout


abstract_tex = pandoc(abstract_md)
body_tex = pandoc(body)

fig1 = r"""\begin{figure*}[tb]
\centering
\includegraphics[width=0.68\textwidth]{fig1.png}
\caption{The zOS stack. A gold frame marks the trusted base: every part a guarantee depends on, isolated or not. The tag says what we know about it. Authority runs from the agent through the broker, motion through the safety controller; there is no third path.}
\end{figure*}"""
fig2 = r"""\begin{figure*}[tb]
\centering
\includegraphics[width=0.68\textwidth]{fig2.png}
\caption{The path from 2026 to 2031. Each station names its evidence and whether it is a demonstration, a test or a proof; a failed check stops the path.}
\end{figure*}"""
body_tex = body_tex.replace("FIGUREONE", fig1).replace("FIGURETWO", fig2).replace("TABLEONE", table_tex)

head, _, refs = body_tex.partition(r"\section{References}")
refs = refs.replace(r"\begin{itemize}", r"\begin{reflist}").replace(r"\end{itemize}", r"\end{reflist}")
refs = refs.replace(r"\tightlist", "")
body_tex = head + r"\section{References}" + "\n{\\footnotesize\n" + refs + "\n}\n"

preamble = r"""\documentclass[11pt,a4paper,twocolumn]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[english]{babel}
\usepackage{charter}
\usepackage[scaled=0.9]{helvet}
\usepackage{textcomp}
\usepackage[protrusion=true,expansion=true]{microtype}
\usepackage[a4paper,top=2.7cm,bottom=2.9cm,left=2.5cm,right=2.5cm,columnsep=0.9cm]{geometry}
\usepackage{graphicx}
\usepackage[font=small,labelfont=bf,labelsep=period,skip=4pt]{caption}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{xcolor}
\usepackage{xurl}
\usepackage{booktabs,longtable,array,calc,tabularx}
\usepackage[colorlinks=true,linkcolor=black,urlcolor={rgb:red,0.10;green,0.25;blue,0.55},pdftitle={zOS - Zero OS},pdfauthor={Tobias von Dewitz, Susann Mürling, Stefan Probst, Daniel Strecker},pdflang={en}]{hyperref}
\providecommand{\tightlist}{\setlength{\itemsep}{1pt}\setlength{\parskip}{0pt}}
\setcounter{secnumdepth}{0}
\titleformat{\section}{\sffamily\bfseries\large}{}{0pt}{}
\titlespacing*{\section}{0pt}{1.2ex plus .4ex minus .2ex}{0.5ex plus .2ex}
\titleformat{\subsection}{\sffamily\bfseries\normalsize}{}{0pt}{}
\titlespacing*{\subsection}{0pt}{1ex plus .3ex minus .2ex}{0.3ex plus .1ex}
\setlist{leftmargin=1.3em,itemsep=1pt,topsep=3pt}
\newlist{reflist}{itemize}{1}
\setlist[reflist]{label={},leftmargin=1.2em,itemindent=-1.2em,itemsep=1.5pt,topsep=2pt}
\setlength{\parindent}{1em}
\linespread{1.05}
\setlength{\parskip}{0pt}
\emergencystretch=1.5em
\renewcommand{\dbltopfraction}{0.85}
\renewcommand{\dblfloatpagefraction}{0.8}
\renewcommand{\topfraction}{0.85}
\renewcommand{\textfraction}{0.1}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\sffamily\footnotesize zOS -- Zero OS}
\fancyhead[R]{\sffamily\footnotesize Working paper 2026-10-23-v0.8}
\fancyfoot[C]{\sffamily\footnotesize \thepage\ / \pageref{LastPage}}
\renewcommand{\headrulewidth}{0.3pt}
\fancypagestyle{first}{\fancyhf{}\renewcommand{\headrulewidth}{0pt}\fancyfoot[C]{\sffamily\footnotesize \thepage\ / \pageref{LastPage}}}
"""

titleblock = r"""\twocolumn[{%
\begin{center}
{\sffamily\footnotesize WORKING PAPER · 2026-10-23-v0.8\par}
\vspace{6pt}
{\sffamily\bfseries\LARGE @TITLE@\textsuperscript{\normalsize *}\par}
\vspace{6pt}
{\large @SUBTITLE@\par}
\vspace{10pt}
{\normalsize Tobias von Dewitz \textperiodcentered{} Susann Mürling \textperiodcentered{} Stefan Probst \textperiodcentered{} Daniel Strecker\par}
{\small 23 October 2026\par}
\vspace{2pt}
{\footnotesize Text and figures: \href{https://creativecommons.org/licenses/by/4.0/}{CC BY 4.0}\par}
{\footnotesize * zOS is a working title. Before its first release the project gets a name of its own, one that treads on nobody's toes, mainframes included.\par}
\end{center}
\vspace{4pt}
\begin{center}
\begin{minipage}{0.86\textwidth}
\small
\noindent{\sffamily\bfseries Abstract.}\enspace @ABSTRACT@
\par\vspace{5pt}
\noindent{\sffamily\bfseries Keywords:}\enspace @KEYWORDS@
\end{minipage}
\end{center}
\vspace{14pt}
}]
\thispagestyle{first}
"""
abstract_flat = abstract_tex.strip().replace("\n\n", "\n\\par\\smallskip\\noindent ")
titleblock = (titleblock.replace("@SUBTITLE@", subtitle)
              .replace("@TITLE@", title.replace("–", "--"))
              .replace("@ABSTRACT@", abstract_flat)
              .replace("@KEYWORDS@", keywords))

doc = preamble + "\\begin{document}\n" + titleblock + body_tex + "\n\\end{document}\n"
(work / "paper.tex").write_text(doc, encoding="utf-8")
print("ok")
