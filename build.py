#!/usr/bin/env python3
"""
build.py — Regenerate publications.html and/or software.html.

    python3 build.py          # rebuild both
    python3 build.py pubs     # publications only  (after adding to hbrefs.bib)
    python3 build.py sw       # software only      (fetches current versions)
"""

import re, sys, json, urllib.request, urllib.error
from pathlib import Path
from collections import defaultdict

ROOT    = Path(__file__).parent
BIB     = ROOT / "hbrefs.bib"
PUB_OUT = ROOT / "publications.html"
SW_OUT  = ROOT / "software.html"


# ── Shared page shell ────────────────────────────────────────────────────

def page(title, active, body):
    tabs = [
        ("index.html",        "Home"),
        ("publications.html", "Publications &amp; Papers"),
        ("teaching.html",     "Teaching"),
        ("software.html",     "Software"),
        ("other.html",        "Other Stuff"),
    ]
    nav = "\n".join(
        f'        <li><a href="{h}"{" class=\"active\"" if h == active else ""}>{lbl}</a></li>'
        for h, lbl in tabs
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
<header>
  <div class="header-inner">
    <div class="site-title"><a href="index.html">Haim Bar, PhD</a></div>
    <div class="site-subtitle">Associate Professor of Statistics &nbsp;·&nbsp; University of Connecticut</div>
    <nav><ul>
{nav}
    </ul></nav>
  </div>
</header>
<main>
{body}
</main>
<footer>
  <p>Haim Bar &nbsp;·&nbsp; Department of Statistics, University of Connecticut
  &nbsp;·&nbsp; <a href="mailto:haim.bar@uconn.edu">haim.bar@uconn.edu</a></p>
</footer>
</body>
</html>"""


# ════════════════════════════════════════════════════════════════════════
# PART 1 — PUBLICATIONS
# ════════════════════════════════════════════════════════════════════════

# ── Static data (talks / presentations / patents) ─────────────────────
# Add new entries to these lists as needed.

INVITED_TALKS = [
    {"title": "High Dimensional Space Oddity.",
     "venues": ("The Joint Statistical Meetings, Nashville, TN, August 2025; "
                "Statistics Department Colloquium, UConn, October 2024.")},
    {"title": "On graphical models and convex geometry.",
     "venues": ("Consortium for Data Analytics in Risk, Berkeley, CA, November 2023; "
                "SIAM Conference on Financial Mathematics and Engineering, Philadelphia, PA, June 2023; "
                "Mathematics and Statistics Department, Old Dominion University, March 2023; "
                "Statistics Department, The Hebrew University, Jerusalem, Israel, June 2022.")},
    {"title": "Large-P Variable Selection in Two-Stage Models.",
     "venues": ("CMStatistics, London, UK, December 2020; "
                "University of Connecticut, March 2020; "
                "University of Haifa, Israel, May 2020.")},
    {"title": "Quantile Regression Modelling via Location and Scale Mixtures of Normal Distributions.",
     "venues": "Cornell University, October 2019."},
    {"title": "A Mixture Model to Detect Edges in Sparse Co-expression Graphs.",
     "venues": ("The 3rd Eastern Asia Meeting on Bayesian Statistics, Seoul, South Korea, July 2018; "
                "Yonsei University, Seoul, South Korea, July 2018; "
                "Korea University, Seoul, South Korea, July 2018; "
                "Bayesian Modeling, Computation, and Applications, Storrs, CT, May 2018.")},
    {"title": "A Scalable Empirical Bayes Approach to Variable Selection in Generalized Linear Models.",
     "venues": ("The 34th Quality and Productivity Research Conference, Storrs, CT, June 2017; "
                "The 10th ICSA International Conference, Shanghai, China, December 2016; "
                "Temple University, Research Colloquium, April 2017; "
                "Baruch College, CUNY, November 2016.")},
    {"title": "A Scalable Empirical Bayes Approach to Variable Selection.",
     "venues": ("2016 Joint Statistical Meetings, Chicago, IL, July 2016; "
                "Joint UConn/UMass Statistics Colloquium, University of Massachusetts Amherst, October 2015; "
                "Statistics Seminar, University of Maryland, October 2015; "
                "Mathematical Biosciences Institute, Ohio State University, September 2015.")},
    {"title": "An Empirical Bayes Approach to Variable Selection and QTL Analysis.",
     "venues": ("Purdue University, Research Colloquium, October 2014; "
                "Modern Modeling Methods (M³) Conference, Storrs, CT, May 2014.")},
    {"title": "Model-based approaches for big-data problems, with applications in genomics.",
     "venues": "Institute for Systems Genomics Annual Networking Workshop, Storrs, CT, May 2014."},
    {"title": "A Bivariate Model for Simultaneous Testing in Bioinformatics Data.",
     "venues": ("3rd International Conference on Biometrics &amp; Biostatistics, Baltimore, MD, October 2014; "
                "University of Iowa, February 2013; "
                "NIH/NCI, March 2013; "
                "University of Connecticut, February 2013; "
                "University of Rochester, February 2013; "
                "Cornell University, October 2012.")},
    {"title": "Accounting for Heaping in Retrospectively Reported Event Data – A Mixture Model Approach.",
     "venues": "ICSA Applied Statistics Symposium, New York City, NY, June 2011."},
    {"title": "A Heap of Trouble? Accounting for Mismatch Bias in Retrospectively Collected Data on Smoking.",
     "venues": "3rd Biennial Conference of the American Society of Health Economists, Ithaca, NY, June 2010."},
]

CONF_PRESENTATIONS = [
    {"title": "High Dimensional Space Oddity.",
     "venues": "Joint Statistical Meetings, Nashville, TN, August 2025."},
    {"title": "On Graphical Models and Convex Geometry.",
     "venues": "SIAM Conference on Financial Mathematics and Engineering, Philadelphia, PA, June 2023."},
    {"title": "Large-P Variable Selection in Two-Stage Models.",
     "venues": "CMStatistics, London, UK, December 2020."},
    {"title": "A Mixture Model to Detect Edges in Sparse Co-expression Graphs.",
     "venues": "3rd Eastern Asia Meeting on Bayesian Statistics, Seoul, South Korea, July 2018."},
    {"title": "A Scalable Empirical Bayes Approach to Variable Selection in Generalized Linear Models.",
     "venues": "10th ICSA International Conference, Shanghai, China, December 2016."},
    {"title": "A Scalable Empirical Bayes Approach to Variable Selection.",
     "venues": "Joint Statistical Meetings, Chicago, IL, July 2016."},
]

PATENTS = [
    {"number": "20230041627", "id": "US20230041627","year": 2023, "date": "published February 9, 2023",
     "desc": "Assay Compound Screening."},
    {"number": "9,384,677",   "id": "US9384677",    "year": 2016, "date": "granted July 5, 2016",    "desc": ""},
    {"number": "9,076,342",   "id": "US9076342",    "year": 2015, "date": "granted July 7, 2015",    "desc": ""},
    {"number": "20150213730", "id": "US20150213730","year": 2015, "date": "published July 30, 2015", "desc": ""},
    {"number": "8,984,396",   "id": "US8984396",    "year": 2015, "date": "granted March 17, 2015",
     "desc": "Identifying and representing changes between XML files. "
             "Inventors: Tingstrom, D.J.; Joyce, R.A.; Stillerman, M.A.; Brueckner, S.K.; Bar, H.Y."},
    {"number": "20150143355", "id": "US20150143355","year": 2015, "date": "published May 21, 2015",
     "desc": "Service Oriented Architecture Version and Dependency Control. "
             "Inventors: Tingstrom, D.J.; Joyce, R.A.; Stillerman, M.A.; Brueckner, S.K.; Bar, H.Y."},
    {"number": "8,898,285",   "id": "US8898285",    "year": 2014, "date": "granted November 25, 2014",
     "desc": "Service Oriented Architecture Version and Dependency Control. "
             "Inventors: Tingstrom, D.J.; Joyce, R.A.; Stillerman, M.A.; Brueckner, S.K.; Bar, H.Y."},
    {"number": "8,286,249",   "id": "US8286249",    "year": 2012, "date": "granted October 9, 2012",  "desc": ""},
    {"number": "7,748,040",   "id": "US7748040",    "year": 2010, "date": "granted June 29, 2010",
     "desc": "Attack correlation using marked information. "
             "Inventors: Adelstein, F.N.; Bar, H.; Alla, P.; Proskourine, N."},
    {"number": "20090208910", "id": "US20090208910","year": 2009, "date": "published August 20, 2009",
     "desc": "Automated execution and evaluation of network-based training exercises. "
             "Inventors: Brueckner, S.; Adelstein, F.N.; Bar, H.; Donovan, M."},
]


# ── LaTeX → plain text/HTML ───────────────────────────────────────────

_GRAVE  = dict(a='à',e='è',i='ì',o='ò',u='ù',A='À',E='È',I='Ì',O='Ò',U='Ù')
_ACUTE  = dict(a='á',e='é',i='í',o='ó',u='ú',A='Á',E='É',I='Í',O='Ó',U='Ú',y='ý')
_UMLAUT = dict(a='ä',e='ë',i='ï',o='ö',u='ü',A='Ä',E='Ë',I='Ï',O='Ö',U='Ü',y='ÿ')
_CEDIL  = dict(c='ç',C='Ç')

def _acc(mapping):
    return lambda m: mapping.get(m.group(1), m.group(1))

def clean(s):
    """Remove LaTeX markup and return HTML-safe text."""
    s = re.sub(r'\\`\{?([a-zA-Z])\}?',  _acc(_GRAVE),  s)
    s = re.sub(r"\\'\{?([a-zA-Z])\}?",  _acc(_ACUTE),  s)
    s = re.sub(r'\{\\"\{?([a-zA-Z])\}?\}', _acc(_UMLAUT), s)
    s = re.sub(r'\\"\{?([a-zA-Z])\}?',  _acc(_UMLAUT), s)
    s = re.sub(r'\\c\{?([cC])\}?',      _acc(_CEDIL),  s)
    s = s.replace(r'\textgreater', '&gt;').replace(r'\textless', '&lt;')
    s = s.replace(r'\&', '&amp;').replace(r'\$', '$').replace(r'\%', '%')
    s = s.replace('---', '—').replace('--', '–')
    s = re.sub(r'\{\\[a-zA-Z]+\}', '', s)   # unknown commands in braces
    s = re.sub(r'\\[a-zA-Z]+\s?', '', s)    # bare commands
    s = s.replace('{', '').replace('}', '')
    return re.sub(r'\s+', ' ', s).strip()


# ── Author formatting ─────────────────────────────────────────────────

def _initial(first):
    first = re.sub(r'\{.*?\}', '', first).strip()
    return (first[0] + '.') if first else ''

def _fmt_one(raw):
    """Format one author as 'Last, F.' with <em> for Bar."""
    raw = raw.strip()
    if ',' in raw:
        last, first = raw.split(',', 1)
    else:
        parts = raw.rsplit(None, 1)
        last, first = (parts[1], parts[0]) if len(parts) == 2 else (parts[0], '')
    last  = clean(last.strip())
    init  = _initial(first)
    fmtd  = f"{last}, {init}" if init else last
    if re.search(r'\bBar\b', last, re.I):
        return f'<em>{fmtd}</em>'
    return fmtd

def fmt_authors(raw):
    parts = re.split(r'\s+and\s+', raw, flags=re.I)
    return '; '.join(_fmt_one(p) for p in parts if p.strip())


# ── BibTeX parser ─────────────────────────────────────────────────────

def _read_value(text, pos):
    """Return (value_string, new_pos) for bib field value starting at pos."""
    if pos >= len(text):
        return '', pos
    ch = text[pos]
    if ch == '{':
        depth, i = 1, pos + 1
        while i < len(text) and depth:
            if   text[i] == '{': depth += 1
            elif text[i] == '}': depth -= 1
            i += 1
        return text[pos+1:i-1], i
    if ch == '"':
        i = pos + 1
        while i < len(text) and text[i] != '"':
            if text[i] == '\\': i += 1
            i += 1
        return text[pos+1:i], i + 1
    # bare number
    m = re.match(r'[\w.]+', text[pos:])
    if m:
        return m.group(), pos + m.end()
    return '', pos

def parse_bib(path):
    text = Path(path).read_text(encoding='utf-8')
    # Fix stray dots in field names (e.g. "volume. =")
    text = re.sub(r'(\w+)\.\s*=\s*', r'\1 = ', text)

    entries, seen_doi = [], set()
    for m in re.finditer(r'@(\w+)\s*\{\s*([^,\s]+)\s*,', text, re.I):
        etype, ekey = m.group(1).lower(), m.group(2)
        if etype in ('string', 'preamble', 'comment'):
            continue
        fields = {'_type': etype, '_key': ekey}
        pos = m.end()
        brace_depth = 1
        while pos < len(text) and brace_depth > 0:
            # skip to next field name or closing brace
            while pos < len(text) and text[pos] in ' \t\n\r,':
                pos += 1
            if pos >= len(text) or text[pos] == '}':
                break
            fm = re.match(r'(\w+)\s*=\s*', text[pos:], re.I)
            if not fm:
                # skip unknown character
                pos += 1
                continue
            fname = fm.group(1).lower()
            pos  += fm.end()
            val, pos = _read_value(text, pos)
            fields[fname] = val.strip()

        # Deduplicate by DOI
        doi = fields.get('doi', '').strip().lstrip('https://doi.org/').lower()
        if doi and doi in seen_doi:
            continue
        if doi:
            seen_doi.add(doi)
        entries.append(fields)
    return entries


# ── Single entry → HTML ───────────────────────────────────────────────

def _doi_link(fields):
    doi = fields.get('doi', '').strip()
    url = fields.get('url', '').strip()
    if doi:
        doi_clean = re.sub(r'^https?://doi\.org/', '', doi)
        href = f"https://doi.org/{doi_clean}"
        return f'<div class="pub-doi"><a href="{href}" target="_blank" rel="noopener">{href}</a></div>'
    if url and url.startswith('http'):
        return f'<div class="pub-doi"><a href="{url}" target="_blank" rel="noopener">{url}</a></div>'
    return ''

def fmt_entry(f):
    authors  = fmt_authors(f.get('author', ''))
    title    = clean(f.get('title', ''))
    year     = f.get('year', '')
    volume   = f.get('volume', '')
    number   = f.get('number', '')
    pages    = f.get('pages', '')
    etype    = f.get('_type', 'article')

    # Normalize page ranges: "3--7" → "3–7"
    pages = re.sub(r'--+', '–', pages)

    if etype == 'incollection':
        ed        = clean(f.get('editor', ''))
        booktitle = clean(f.get('booktitle', ''))
        publisher = clean(f.get('publisher', ''))
        pg        = pages
        journal_html = f'In {ed} (Ed.), <em>{booktitle}</em>'
        if pg:  journal_html += f', pp. {pg}'
        if publisher: journal_html += f'. {publisher}.'
    else:
        journal = clean(f.get('journal', f.get('booktitle', '')))
        detail  = journal
        # Skip placeholder values (e.g. volume=0 or number="ja" for just-accepted papers)
        vol_ok = volume and volume not in ('0',)
        num_ok = number and number.lower() not in ('ja', '0')
        if vol_ok:              detail += f', {volume}'
        if vol_ok and num_ok:   detail += f'({number})'
        if pages:               detail += f', {pages}'
        journal_html = f'<em>{detail}</em>.'

    return (
        f'      <li class="pub-item">\n'
        f'        <div class="pub-authors">{authors}</div>\n'
        f'        <div class="pub-title">{title}.</div>\n'
        f'        <div class="pub-journal">{journal_html}</div>\n'
        f'        {_doi_link(f)}\n'
        f'      </li>'
    )


# ── Build publications.html ───────────────────────────────────────────

def build_publications():
    entries = parse_bib(BIB)

    by_year = defaultdict(list)
    for e in entries:
        try:
            yr = int(e.get('year', 0))
        except ValueError:
            yr = 0
        by_year[yr].append(e)

    # Papers section
    pub_html = ['  <h1>Publications &amp; Papers</h1>',
                '  <p style="color:var(--muted); font-size:.9rem;">Jump to: '
                '<a href="#papers">Peer-Reviewed Papers</a> &nbsp;·&nbsp; '
                '<a href="#talks">Invited Talks</a> &nbsp;·&nbsp; '
                '<a href="#presentations">Selected Conference Presentations</a> &nbsp;·&nbsp; '
                '<a href="#patents">Patents</a></p>',
                '  <h2 id="papers">Peer-Reviewed Publications</h2>']

    for yr in sorted(by_year, reverse=True):
        if yr == 0:
            continue
        pub_html.append(f'  <div class="year-group">\n    <div class="year-label">{yr}</div>')
        pub_html.append('    <ul class="pub-list">')
        for e in by_year[yr]:
            pub_html.append(fmt_entry(e))
        pub_html.append('    </ul>\n  </div>')

    # Invited talks
    pub_html.append('  <h2 id="talks">Invited Talks</h2>\n  <ul class="talk-list">')
    for t in INVITED_TALKS:
        pub_html.append(
            f'    <li class="talk-item">'
            f'<span class="talk-title">{t["title"]}</span> '
            f'{t["venues"]}</li>'
        )
    pub_html.append('  </ul>')

    # Conference presentations
    pub_html.append('  <h2 id="presentations">Selected Conference Presentations</h2>\n  <ul class="talk-list">')
    for p in CONF_PRESENTATIONS:
        pub_html.append(
            f'    <li class="talk-item">'
            f'<span class="talk-title">{p["title"]}</span> '
            f'{p["venues"]}</li>'
        )
    pub_html.append('  </ul>')

    # Patents — grouped by year
    pub_html.append('  <h2 id="patents">Patents</h2>')
    patents_by_year = defaultdict(list)
    for p in PATENTS:
        patents_by_year[p['year']].append(p)
    for yr in sorted(patents_by_year, reverse=True):
        pub_html.append(f'  <div class="year-group">\n    <div class="year-label">{yr}</div>')
        pub_html.append('    <ul class="patent-list">')
        for p in patents_by_year[yr]:
            link = f'https://patents.google.com/patent/{p["id"]}'
            desc = f' {p["desc"]}' if p['desc'] else ''
            pub_html.append(
                f'      <li class="patent-item">'
                f'<strong><a href="{link}" target="_blank" rel="noopener">'
                f'U.S. Patent {p["number"]}</a></strong> ({p["date"]}).{desc}</li>'
            )
        pub_html.append('    </ul>\n  </div>')

    body = '\n'.join(pub_html)
    PUB_OUT.write_text(page('Publications – Haim Bar, PhD', 'publications.html', body),
                       encoding='utf-8')
    n = sum(len(v) for v in by_year.values())
    print(f"publications.html written  ({n} entries across {len(by_year)} years)")


# ════════════════════════════════════════════════════════════════════════
# PART 2 — SOFTWARE
# ════════════════════════════════════════════════════════════════════════

# ── Version fetchers ──────────────────────────────────────────────────

def _fetch_json(url):
    import ssl
    # Try verified SSL first; fall back to unverified for macOS cert configuration issues.
    for ctx in (ssl.create_default_context(), ssl._create_unverified_context()):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'build.py/1.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
                return json.loads(r.read())
        except Exception as e:
            if 'ssl' in str(e).lower() or 'certificate' in str(e).lower():
                continue   # retry with unverified context
            print(f"  [warn] {url}: {e}")
            return None
    print(f"  [warn] SSL error fetching {url}")
    return None

GITHUB_DIR = Path.home() / "Documents" / "GitHub"

def fetch_version(source):
    """Return current version string or '?' on failure."""
    kind, name = source
    if kind == 'manual':
        return name
    if kind == 'local':
        # Read Version: field from a local R package DESCRIPTION file
        desc = GITHUB_DIR / name / "DESCRIPTION"
        if desc.exists():
            m = re.search(r'^Version:\s*(\S+)', desc.read_text(), re.M)
            return m.group(1) if m else '?'
        return '?'
    if kind == 'pypi':
        data = _fetch_json(f'https://pypi.org/pypi/{name}/json')
        if data:
            return data['info']['version']
    if kind == 'ctan':
        data = _fetch_json(f'https://www.ctan.org/json/2.0/pkg/{name}')
        if data:
            ver = data.get('version', {})
            return ver.get('number', ver.get('text', '?'))
    if kind == 'cran':
        data = _fetch_json(f'https://crandb.r-pkg.org/{name}')
        if data:
            return data.get('Version', '?')
    if kind == 'github':
        # Try latest release first, fall back to latest tag
        data = _fetch_json(f'https://api.github.com/repos/{name}/releases/latest')
        if data and 'tag_name' in data:
            return data['tag_name'].lstrip('v')
        tags = _fetch_json(f'https://api.github.com/repos/{name}/tags')
        if tags:
            return tags[0]['name'].lstrip('v')
    return '?'


# ── Software package definitions ──────────────────────────────────────
# version_source: ('pypi'|'ctan'|'github'|'manual'), package-name/repo/version
# For github sources, name is "owner/repo"

SOFTWARE = [
    {
        'name':    'runcode — LaTeX Package for Reproducible Science',
        'badges':  [('CTAN', 'badge-ctan'), ('GitHub', 'badge-github')],
        'ver_src': ('ctan', 'runcode'),
        'ver_note':'Co-authored with HaiYing Wang · License: LPPL 1.3c',
        'desc': (
            'A LaTeX package that executes external code (R, Python, Julia, Matlab, and any '
            'command-line tool) from within a LaTeX document and embeds the output directly in '
            'the compiled PDF. Designed for fully reproducible scientific documents. Works in '
            'server mode via the <strong>talk2stat</strong> Python package. '
            'Available through TeX&nbsp;Live and MiKTeX.'
        ),
        'links': [
            ('CTAN page',      'https://ctan.org/pkg/runcode'),
            ('GitHub',         'https://github.com/Ossifragus/runcode'),
            ('Paper (JDS 2021)', 'https://doi.org/10.6339/21-JDS998'),
        ],
    },
    {
        'name':    'talk2stat — Python Package',
        'badges':  [('PyPI', 'badge-pypi'), ('GitHub', 'badge-github')],
        'ver_src': ('pypi', 'talk2stat'),
        'ver_note':'Requires: pexpect',
        'desc': (
            'Opens and manages a bidirectional socket connection to R, Julia, Python, or Matlab, '
            'enabling other programs (such as the <strong>runcode</strong> LaTeX package) to send '
            'code and receive output without re-launching the interpreter.'
        ),
        'links': [
            ('PyPI',   'https://pypi.org/project/talk2stat/'),
            ('GitHub', 'https://github.com/Ossifragus/talk2stat'),
        ],
    },
    {
        'name':    'loopmonitor — Loop Control for Long-Running Programs (Python)',
        'badges':  [('PyPI', 'badge-pypi'), ('GitHub', 'badge-github')],
        'ver_src': ('pypi', 'loopmonitor'),
        'ver_note':'',
        'desc': (
            'Provides on-demand status queries and graceful control of long-running Python loops '
            'without interrupting execution. Drop-in replacements for <code>for</code> / '
            '<code>while</code> loops write a JSON state file after every iteration; an '
            '<code>ipc</code> command-line tool lets you peek at progress, plot tracked values, '
            'set variables, or break the loop from a second terminal. '
            'Companion R package also available.'
        ),
        'links': [
            ('PyPI',   'https://pypi.org/project/loopmonitor/'),
            ('GitHub', 'https://github.com/haimbar/loopmonitor'),
        ],
    },
    {
        'name':    'loopmonitor — Loop Control for Long-Running Programs (R)',
        'badges':  [('GitHub', 'badge-github'), ('R', 'badge-r')],
        'ver_src': ('manual', '0.1.0'),
        'ver_note':'Requires: jsonlite · Companion to the Python loopmonitor package',
        'desc': (
            'Provides <code>ipc_for()</code>, <code>ipc_while()</code>, and '
            '<code>ipc_repeat()</code> as drop-in replacements for R\'s loop constructs, '
            'enabling on-demand inspection and control of long-running loops from a second '
            'terminal using the <code>ipc</code> command-line tool. Status, tracked values, '
            'and ETA are written to a JSON state file after every iteration.'
        ),
        'links': [
            ('GitHub', 'https://github.com/haimbar/loopmonitor-r'),
        ],
    },
    {
        'name':    'edgefinder — Gene Network Inference (Python)',
        'badges':  [('PyPI', 'badge-pypi'), ('GitHub', 'badge-github')],
        'ver_src': ('manual', '0.1.10'),
        'ver_note':'',
        'desc': (
            'Recovers gene network structure from co-expression data using a mixture-model '
            'approach based on convex geometry and beta distributions. Controls edge detection '
            'error rates without assuming network sparsity. Includes simulation code and case studies.'
        ),
        'links': [
            ('PyPI',           'https://pypi.org/project/edgefinder/'),
            ('Paper (PLOS ONE 2021)', 'https://doi.org/10.1371/journal.pone.0246945'),
            ('Paper (CSDA 2023)',     'https://doi.org/10.1016/j.csda.2023.107800'),
        ],
    },
    {
        'name':    'QREM — Quantile Regression via EM Algorithm (R)',
        'badges':  [('GitHub', 'badge-github'), ('R', 'badge-r')],
        'ver_src': ('local', 'QREM'),
        'ver_note':'',
        'desc': (
            'Implements mixed-effects quantile regression and variable selection via an EM '
            'algorithm. Suitable for high-dimensional settings where standard quantile '
            'regression methods may be unstable.'
        ),
        'links': [
            ('GitHub', 'https://github.com/haimbar/QREM'),
            ('Paper (Statistical Modelling 2021)', 'https://doi.org/10.1177/1471082X211033490'),
        ],
    },
    {
        'name':    'SEMMS — Scalable EMpirical Bayes Model Selection (R)',
        'badges':  [('GitHub', 'badge-github'), ('R', 'badge-r')],
        'ver_src': ('manual', '0.2.5'),
        'ver_note':'Includes datasets and vignette',
        'desc': (
            'Variable selection for generalized linear models using a scalable empirical Bayes '
            'approach. Suitable for high-dimensional problems where the number of predictors is '
            'large relative to sample size.'
        ),
        'links': [
            ('Paper (JCGS 2020)', 'https://doi.org/10.1080/10618600.2019.1706542'),
            ('arXiv',             'https://arxiv.org/abs/2603.15902'),
        ],
    },
    {
        'name':    'DVX — Differential Variation and Expression (R)',
        'badges':  [('GitHub', 'badge-github'), ('R', 'badge-r')],
        'ver_src': ('manual', ''),
        'ver_note':'',
        'desc': (
            'An interactive R program for simultaneous analysis of differential variation and '
            'differential expression in genomic data.'
        ),
        'links': [
            ('Paper (Stat 2019)', 'https://doi.org/10.1002/sta4.237'),
        ],
    },
    {
        'name':    'R-CMap — Concept Mapping Software (R)',
        'badges':  [('GitHub', 'badge-github'), ('R', 'badge-r')],
        'ver_src': ('local', 'RCMap'),
        'ver_note':'',
        'desc': (
            'Open-source concept mapping software. Provides tools for data collection, '
            'multidimensional scaling, cluster analysis, and visualization. Used in social '
            'sciences, public health, and education research.'
        ),
        'links': [
            ('GitHub', 'https://github.com/haimbar/RCMap'),
            ('Paper (Evaluation and Program Planning 2017)', 'https://doi.org/10.1016/j.evalprogplan.2016.08.018'),
        ],
    },
    {
        'name':    'betaMix — Beta Mixture Models for Correlation (R)',
        'badges':  [('GitHub', 'badge-github'), ('R', 'badge-r')],
        'ver_src': ('local', 'betaMix'),
        'ver_note':'',
        'desc': (
            'Identifies significant correlations in high-dimensional data using a mixture '
            'of beta distributions framework. Applications include graphical model selection '
            'and network inference. Also available in Python (betaMixPy).'
        ),
        'links': [
            ('GitHub (R)',      'https://github.com/haimbar/betaMix'),
            ('GitHub (Python)', 'https://github.com/haimbar/betaMixPy'),
            ('Paper (CSDA 2023)', 'https://doi.org/10.1016/j.csda.2023.107800'),
        ],
    },
    {
        'name':    'Spatial Capture-Recapture MCMC Code (R)',
        'badges':  [('GitHub', 'badge-github'), ('R', 'badge-r')],
        'ver_src': ('manual', ''),
        'ver_note':'Co-authored with Paul McLaughlin, PhD',
        'desc': (
            'Bayesian MCMC implementation for a spatial capture-recapture model with '
            'inter-individual attraction terms. Estimates animal abundance and movement patterns.'
        ),
        'links': [
            ('Paper (Environmetrics 2021)', 'https://doi.org/10.1002/env.2653'),
        ],
    },
]


# ── Build software.html ───────────────────────────────────────────────

def _badge(label, cls):
    return f'<span class="badge {cls}">{label}</span>'

def build_software():
    items = []
    for pkg in SOFTWARE:
        print(f"  fetching version for {pkg['name'].split('—')[0].strip()} ...", end=' ', flush=True)
        ver = fetch_version(pkg['ver_src'])
        print(ver)

        badges = ' '.join(_badge(lbl, cls) for lbl, cls in pkg['badges'])
        ver_line = ''
        if ver and ver != '?':
            ver_line = f'Version {ver}'
        if pkg['ver_note']:
            ver_line = (ver_line + ' &nbsp;·&nbsp; ' + pkg['ver_note']) if ver_line else pkg['ver_note']

        links = ' '.join(
            f'<a href="{url}" target="_blank" rel="noopener">{lbl}</a>'
            for lbl, url in pkg['links']
        )

        items.append(
            f'    <li class="software-item">\n'
            f'      <div class="software-name">{pkg["name"]}</div>\n'
            f'      <div class="software-badges">{badges}</div>\n'
            f'      <div class="software-desc">{pkg["desc"]}</div>\n'
            + (f'      <div class="software-desc" style="color:var(--muted);">{ver_line}</div>\n' if ver_line else '')
            + f'      <div class="software-links">{links}</div>\n'
            f'    </li>'
        )

    body = (
        '  <h1>Software</h1>\n'
        '  <p>Packages developed by Haim Bar and collaborators, freely available on '
        'GitHub, CRAN, PyPI, and CTAN.</p>\n'
        '  <ul class="software-list">\n'
        + '\n'.join(items)
        + '\n  </ul>'
    )
    SW_OUT.write_text(page('Software – Haim Bar, PhD', 'software.html', body),
                      encoding='utf-8')
    print(f"software.html written  ({len(SOFTWARE)} packages)")


# ════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else 'all'
    if arg in ('all', 'pubs'):
        build_publications()
    if arg in ('all', 'sw', 'software'):
        build_software()
    if arg not in ('all', 'pubs', 'sw', 'software'):
        print("Usage: build.py [pubs | sw]   (default: both)")
