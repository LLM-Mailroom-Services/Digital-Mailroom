/* THE MAILROOM terminal site — static data payloads.
   Generated/hand-maintained alongside tui/repos.py (same constellation). */
'use strict';

const MAILROOM_DATA = {
  banner: String.raw`
___ ___ ___ ___ ___ ___ ___ ___ ___
|_   _| | _ \_ _| \| |_ _| __| _ \ _ \
  | | | ||   / | || .  || || _||   /   /
  |_| |___|_|_\\___|_|\_|___|___|_|_\_|_\
`,
  motd: [
    'welcome to the llm-mailroom — the multi-agent pipeline that ingests',
    'high-volume legal documents, classifies them, routes them to specialist',
    'agents, and archives every decision with a full audit trail.',
    '',
    "type 'help' to begin.  type 'ls' to look around.  type 'corpus ls'",
    "to browse the 3,302-row mailroom-dataset corpus on the Hub.",
    "the floor is live; the archive is immutable; every run is traced.",
  ],
  lore: [
    'every run you see here was traced through Langfuse. nothing is canned.',
    'the sorter never sleeps. the judge grades every ambiguous extraction.',
    'the archive is hash-chained: every file and every decision, sealed.',
    'between these trays, a small pixel console is rendering envelopes.',
    'the corpus remembers. that is its whole job.',
  ],
  repos: [
    { name: 'llm-mailroom', role: 'pipeline', dist: 'mailroom',
      url: 'https://github.com/Exios66/llm-mailroom',
      blurb: 'Multi-agent pipeline: ingests high-volume legal documents, classifies them, routes them to specialist agents for extraction, compiles matter records, and archives everything with a full audit trail.' },
    { name: 'The-Mailroom', role: 'visualizer', dist: 'the-mailroom',
      url: 'https://github.com/Exios66/The-Mailroom',
      blurb: 'Pixel-art visual engine for the llm-mailroom pipeline — this very site. Every displayed value is derived from Langfuse traces.' },
    { name: 'llm-dojo-scoring', role: 'scoring', dist: 'llm-dojo-scoring',
      url: 'https://github.com/Exios66/llm-dojo-scoring',
      blurb: 'Dedicated scoring, error-analysis, visualization, and interpretation suite for LLM document pipelines — a single importable library.' },
    { name: 'llm-entity-extraction', role: 'eval', dist: 'llm-entity-extraction',
      url: 'https://github.com/Exios66/llm-entity-extraction',
      blurb: 'Training & evaluation environment to identify strong LLM candidates for legal document entity extraction, classification, and summarization.' },
    { name: 'agent-mailroom', role: 'pipeline', dist: 'agent-mailroom',
      url: 'https://github.com/Exios66/agent-mailroom',
      blurb: 'Self-contained legal-document mailroom: one state machine per document, specialist agents at desks, a hash-chained audit log, and a pixel floor where envelopes fly from reception to the boss.' },
    { name: 'local-mailroom-sandbox', role: 'sandbox', dist: 'mailroom-sandbox',
      url: 'https://github.com/Exios66/local-mailroom-sandbox',
      blurb: 'Sandbox for developing & testing the LLM mailroom pipeline with offline/localized models.' },
    { name: 'Enron-Evaluation-Environment', role: 'corpus', dist: 'enron-evaluation-environment',
      url: 'https://github.com/Exios66/Enron-Evaluation-Environment',
      blurb: 'Exploratory data analysis of the CMU classic Enron email corpus and the production of a pipeline-ready correspondence dataset.' },
    { name: 'claims-data-eda', role: 'corpus', dist: 'claims-data-eda',
      url: 'https://github.com/Exios66/claims-data-eda',
      blurb: 'Exploratory data analysis of real insurance-claim samples from the mailroom-corpus (carrier / inpatient / outpatient / PDE strata).' },
    { name: 'llm-mailroom-graph', role: 'derived', dist: 'llm-mailroom-graph',
      url: 'https://github.com/Exios66/llm-mailroom-graph',
      homepage: 'https://exios66.github.io/llm-mailroom-graph/',
      blurb: 'Interactive graphify knowledge graph of llm-mailroom — a derived artifact site rebuilt from the source repo.' },
    { name: 'mailroom-corpus-eda', role: 'corpus', dist: 'mailroom-corpus-eda',
      url: 'https://github.com/Exios66/Mailroom-Corpus-EDA',
      blurb: 'Dedicated repository for the full HF LLM-Mailroom corpus exploratory data analysis + the centralized Hub upload helpers (mailroom-corpus dataset family).' },
    { name: 'mailroom-dev', role: 'hub', dist: 'mailroom-hub',
      url: 'https://github.com/Exios66/mailroom-dev',
      blurb: 'The monorepo of the LLM-Mailroom project (this workspace) — one uv workspace, one lockfile, all feeder repositories mirrored as packages. Canonical hub URL.' },
    { name: 'mailroom-hub', role: 'hub', dist: 'mailroom-hub',
      url: 'https://github.com/Exios66/mailroom-hub',
      blurb: 'Monorepo mirror of Exios66/mailroom-dev under the mailroom-hub release name (CHANGELOG + release chain + vX.Y.Z tags).' },
    { name: 'LLM-Postal', role: 'hub', dist: 'mailroom-hub',
      url: 'https://github.com/Exios66/LLM-Postal',
      blurb: 'Monorepo mirror of the LLM-Mailroom constellation — one checkout, one virtualenv, ten packages, zero cross-repo import friction.' },
    { name: 'mailroom-dev-graph', role: 'derived', dist: 'mailroom-dev-graph',
      url: 'https://github.com/Exios66/mailroom-dev-graph',
      homepage: 'https://exios66.github.io/mailroom-dev-graph/',
      blurb: 'Interactive graphify knowledge graph of the mailroom-dev monorepo — 4,870 code symbols, 16,161 edges, 325 communities across 9 packages.' },
    { name: 'llm-entity-extraction-graph', role: 'derived', dist: 'llm-entity-extraction-graph',
      url: 'https://github.com/Exios66/llm-entity-extraction-graph',
      blurb: 'Interactive graphify knowledge graph of llm-entity-extraction — a derived artifact site.' },
  ],
  about: [
    '## whoami — the operator desk',
    '',
    'You are at the console of **THE MAILROOM**, the visual engine for the',
    'llm-mailroom multi-agent legal-document pipeline.',
    '',
    'Every document enters the floor through an intake sorter, is classified,',
    'routed to a specialist agent for extraction, judged, arbitrated when the',
    'verdict is partial, and compiled into a matter record — then everything',
    'is archived with an auditable hash chain.  The reviewer queue holds the',
    'runs that need a human.',
    '',
    'This terminal is one of four faces of the visualizer:',
    '',
    '| surface | what it is |',
    '|---|---|',
    '| this terminal | the root page — a TTY into the floor, corpus, and constellation |',
    '| pixel console | the CRT conveyor floor (`pixel` to jump to `/pixel/`) |',
    '| observatory | the hosted /live desk (live server only) |',
    '| mailroom-tui | the same console in your own terminal — `pip install -e . && mailroom-tui` |',
    '',
    '**Langfuse is the sole source of truth.**  Every run, span, and score you',
    'see was traced by the pipeline; the corpus views read the Hub dataset',
    '`Lucius-Morningstar/mailroom-dataset` (3,302 rows).',
    '',
    'Type `help` for the full command list, or `ls` to look around.',
  ],
  plan: [
    '## .plan — what the floor is doing',
    '',
    '- **Intake** — deterministic cleaning + LLM-assisted prep, sliding windows, no truncation.',
    '- **Classify** — sorter with retry + review; free-model Gmail triage lane for single documents.',
    '- **Extract** — specialist agents per doc class; judge gate on the ambiguous band; arbiter on partials.',
    '- **Report** — matter record compilation (procedural in v0.6.0).',
    '- **Archive** — auditable hash archive; every file and every decision sealed.',
    '- **Review** — runs waiting on a human land on the REVIEW siding.',
    '',
    'Milestones: M1 data core · M2 pixel engine · M3 live mode · M4 TUI console ·',
    'M5 polish · v0.3.0 GH Pages edition · v0.4.0 terminal REPL + this site.',
  ],
  contact: [
    '## .contact — reaching the humans',
    '',
    'The pipeline watches a Gmail inbox for single-document uploads, and the',
    'watcher emails status alerts (up / down) to the operator address.',
    '',
    '- **operator email**: `axios337@gmail.com`  (also the status-alert recipient)',
    '- **constellation**: `https://github.com/Exios66` — the repos behind the floor',
    '- **corpus**: `https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset`',
    '',
    'From here, `mail` opens a composer that hands the finished message to',
    'your mail client.',
  ],
  help: `NAME
    mailroom - the llm-mailroom pipeline, in terminal form

SYNOPSIS
    <command> [arguments]

DESCRIPTION
    You are watching a multi-agent legal-document pipeline by typing
    commands at a prompt. Output above; prompt below; the floor is
    live.

COMMANDS
    help              show this message (man-style, animated)
    man <command>     manual for a command
    ls [path]         list the virtual filesystem
    cat <file>        read a file (markdown-rendered)
    cd <dir>          change directory (topics/<class> filters by tag)
    pwd               print working directory
    tree              show the filesystem tree
    floor             the live pipeline desk (runs in the window)
    inspect <id>      drill into one run's spans, generations, scores
    review            runs waiting on a human
    metrics           window aggregates (cost, tokens, verdicts)
    sessions          Langfuse matters
    corpus ls         browse the Hub dataset catalog
    corpus show <f>   full document text + ground truth for one file
    corpus search <t> match filename / class / subclass
    corpus stats      row counts per split and per doc class
    repos             the LLM-Mailroom constellation
    repos <name>      one repo's blurb and links
    open <name|url>   open a repo or URL in a new tab
    search <terms>    search runs and corpus filenames
    whoami            who you are and what this is
    mail [addr]       compose a message to the operator
    neofetch          the mailroom banner
    history           show command history
    clear             clear screen (also Ctrl+L)
    date              current date and time
    echo <text>       print text back
    uname             system name

SETTINGS
    theme [name]      amber | green | cyan
    crt [on|off]      toggle the CRT scanline overlay
    sound [on|off]    toggle keypress sound
    skyline [on|off]  toggle the ambient mailroom skyline

LINKS
    pixel             the pixel console (/pixel/ on this site)
    observatory       the hosted /live desk (live server only)
    hub               the mailroom-dataset corpus on Hugging Face
    tui               how to run mailroom-tui in your own terminal

KEYBOARD
    Tab               complete the current word (grey ghost text)
    Up / Down         navigate command history
    Right / End       accept the ghost-text suggestion
    Ctrl+L            clear screen
    Ctrl+C            cancel current line

TIPS
    The virtual filesystem:
      ls
      cd runs
      cd corpus
      cd topics/insurance_claim
      cat README.md
    The dataset is live on the Hub — 'corpus show' fetches real rows:
      corpus ls --class contract
      corpus show <filename>
    The constellation is one 'repos' away:
      repos
      repos llm-mailroom
      open llm-dojo-scoring

AUTHOR
    The llm-mailroom agents, supervised by humans.

REPORTING BUGS
    There are no bugs. There are only unplanned features of the floor.`,
  manPages: {
    ls: `LS(1)

NAME
    ls - list directory contents

SYNOPSIS
    ls [directory]

DESCRIPTION
    List files and subdirectories. Without arguments, lists the
    current working directory.

    Output is color-coded:
      cyan    directories
      amber   markdown entries / run files
      dim     hidden (dot) files

    Virtual directories:
      ~/runs        pipeline runs in the window (cat one to read it)
      ~/corpus      the mailroom-dataset corpus (cat a file for its
                    document text + ground truth)
      ~/repos       the constellation repositories
      ~/topics      doc-class tags (cd topics/<class> filters)

EXAMPLES
    ls
    ls runs
    ls corpus
    ls topics/insurance_claim`,
    cat: `CAT(1)

NAME
    cat - concatenate and print files

SYNOPSIS
    cat <file>

DESCRIPTION
    Print the contents of a file. Markdown entries are rendered
    with formatting: headings, bold, italic, code, lists, tables,
    blockquotes and links.

    - runs/<id> prints a run's story (stages, verdict, scores)
    - corpus/<file> prints the document text + ground truth
    - repos/<name> prints the repo blurb and GitHub link

EXAMPLES
    cat README.md
    cat .plan
    cat runs/contract_03_service_agreement.pdf
    cat corpus/0001062993-15-000198_s1011515_ex3z2.htm
    cat repos/llm-mailroom`,
    cd: `CD(1)

NAME
    cd - change working directory

SYNOPSIS
    cd [directory]

DESCRIPTION
    Change the current working directory. Without arguments,
    returns to the home directory (~).

    Special values:
      ..    parent directory
      ~     home directory

    topics/<tag> is a virtual directory holding every corpus file
    that carries that doc class.

EXAMPLES
    cd runs
    cd corpus
    cd topics/contract
    cd ..`,
    floor: `FLOOR(1)

NAME
    floor - the live pipeline desk

SYNOPSIS
    floor

DESCRIPTION
    Prints every run in the recent window: file, station, doc
    type, confidences, verdict, quality, cost, routing path.

    The data is a static snapshot of the Langfuse trace source,
    exported at publish time by scripts/export_snapshot.py — the
    live floor lives on the running server / mailroom-tui.`,
    inspect: `INSPECT(1)

NAME
    inspect - drill into one run

SYNOPSIS
    inspect <trace-id>

DESCRIPTION
    Prints the full run detail — spans, LLM generations, scores —
    from the exported snapshot.

EXAMPLES
    floor
    inspect <a trace id from the floor>`,
    corpus: `CORPUS(1)

NAME
    corpus - browse the mailroom-dataset Hub corpus

SYNOPSIS
    corpus ls [--class X] [--split train|test] [--page N] [--limit N]
    corpus show <filename>
    corpus search <term> [--split X] [--limit N]
    corpus stats

DESCRIPTION
    Views Lucius-Morningstar/mailroom-dataset (3,302 rows)
    through Hugging Face's datasets-server.

      ls       slim listing from the bundled catalog (instant,
               works offline)
      show     full document text + ground-truth fields, fetched
               live from the Hub one row at a time
      search   match term against filename / class / subclass
      stats    row counts per split and per doc class

    The Hub being unreachable is an explicit closed state — the
    terminal never shows canned data.

EXAMPLES
    corpus ls --class insurance_claim --limit 25
    corpus show 0001062993-15-000198_s1011515_ex3z2.htm
    corpus search correspondence
    corpus stats`,
    repos: `REPOS(1)

NAME
    repos - the LLM-Mailroom constellation

SYNOPSIS
    repos
    repos <name>
    open <name>

DESCRIPTION
    Lists the standalone Exios66 repositories that make up the
    constellation: pipeline, visualizer, scoring, eval, sandbox,
    corpus feeds, derived graph sites, and the hub monorepo.
    'open' jumps to a repo page in a new tab.

EXAMPLES
    repos
    repos llm-mailroom
    open llm-dojo-scoring`,
    whoami: `WHOAMI(1)

NAME
    whoami - about the mailroom

SYNOPSIS
    whoami

DESCRIPTION
    Prints the operator-desk page: what this is, the four faces of
    the visualizer, and the source-of-truth doctrine.`,
    mail: `MAIL(1)

NAME
    mail - compose a message to the operator

SYNOPSIS
    mail [address]

DESCRIPTION
    Compose a message. After invoking the command you will be
    prompted for a subject and body. End the body with a single
    '.' on its own line, or press Ctrl+D.

    There is no SMTP server here — this is a static site — so the
    finished message is handed to your mail client as a mailto:
    link.`,
    theme: `THEME(1)

NAME
    theme - change the phosphor color theme

SYNOPSIS
    theme [name]

AVAILABLE THEMES
    amber   - IBM 3270 amber (default)
    green   - VT100 phosphor green
    cyan    - modern terminal cyan`,
  },
};