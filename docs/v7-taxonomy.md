# v7 taxonomy contract

**Status:** canonical terminology for the `Lucius-Morningstar/mailroom-corpus` v7 corpus and its relationship to the live Mailroom taxonomy.

## 1. The key distinction

The phrase **"v7 five-class corpus"** is the correct description of the document-class surface represented in `mailroom-corpus` v7 (the Hub dataset renamed from `docclass-merged` on 2026-09-02 — "docclass" was a placeholder; the v7 git history, pinned revision `bb57c5ad`, and all revisions survived the rename).

The phrase **"five-class live Mailroom taxonomy"** is the correct description of the current Mailroom production taxonomy.

These are now aligned:

- The live pipeline taxonomy contains five classes.
- The v7 Hugging Face corpus represents all five classes.
- `compliance_filing` has been retired from the canonical corpus/evaluation surface and is no longer a live document class (its pipeline-config remnant is marked `status: retired` — see §4).
- `court` and `dd` are retired and are not v7 classes.

Therefore, v7 should be described as the **five-class corpus using the five-class live Mailroom taxonomy, with class × subclass strata represented for those five classes**.

## 2. Canonical vocabularies

### Live Mailroom document classes

```text
contract
merger_agreement
corporate_record
correspondence
insurance_claim
```

### v7 represented document classes

```text
contract
merger_agreement
corporate_record
correspondence
insurance_claim
```

The v7 corpus therefore has **5 represented document classes**, with complete top-level class coverage of the live pipeline taxonomy.

### Subclass

`expected_subclass` is a **second-level document-type label**, not another document class and not an intent label.

Examples used by the current sandbox/fixtures include:

| Document class | Example subclass |
| --- | --- |
| `contract` | `Consulting Agreements` |
| `merger_agreement` | `all_cash` |
| `corporate_record` | `bylaws` |
| `correspondence` | `attorney_demand` |
| `insurance_claim` | `carrier` |

The exact subclass vocabulary is corpus-derived and should be treated as a stratum vocabulary, not promoted into the top-level production taxonomy unless explicitly adopted by the pipeline configuration.

**v8 subclass strata (HUB-028, pinned `eafe1ab4`; HUB-041 alignment):** the
v8 insurance LOB expansion grew the corpus to 2,000 rows / 50 strata and the
insurance_claim subclass vocabulary from the four CMS file types to six:

```text
carrier · inpatient · outpatient · pde · property · auto
```

(`property` = 200 GNOTHEIA FNOL bundles, `auto` = 150 BDR motor decision
letters; CMS rows keep `claim_type = health`). The pipeline configuration has
since explicitly adopted this vocabulary on the subclass surfaces — the dojo
subclass catalogs, the entity taxonomy `subclasses:` blocks + sorter subclass
lists + the `sorter_mailroom_*` prompt lineages, The-Mailroom's
`DOC_SUBCLASS_BY_CLASS`, and the mailroom sorter guard — and the
taxonomy-parity gate (HUB-041 subclass layer) pins every surface to the Hub
GT vocabulary.

## 3. Intent is a separate dimension

Correspondence intent is **not a subclass**.

For v7, correspondence rows may carry canonical intent plus provenance fields:

```text
intent
intent_source
intent_confidence
intent_status
```

For example, `payment_demand` is an intent value. It should not be described as a correspondence subclass merely because it is evaluated alongside class/subclass fields.

This gives the v7 label model three distinct concepts:

```text
Document class
    └── expected_subclass

Correspondence-specific semantic dimension
    └── intent + intent provenance

Extraction target dimension
    └── expected_fields
```

## 4. Why issue #7 needs this wording

The pending GEPA task refers to a "5 doc class & associated subclass set." The intended experiment should be recorded as:

> **Sorter prompt mutation on the v7 five-class corpus, using the class × subclass strata represented by `mailroom-corpus` v7.**

The experiment now evaluates the same five top-level classes used by the production pipeline. `compliance_filing` is not part of the canonical sorter output contract or any corpus/evaluation surface.

**Removal state (verified 2026-09-15):** the config-driven sorter label
set, prompt catalog, and specialist dispatch no longer resolve the
compliance class — commit `59c47401` (2026-09-15) **removed** its
`doc_classes` entry from `packages/llm-mailroom/src/config/taxonomy.yaml`
outright (zero Hub rows); no `status: retired` marker remains and nothing
is retained. The five-class roster plus `unknown` is final, and the
taxonomy-parity gate's retired roster treats all former classes as
historical vocabulary, not drift — but only as historical vocabulary:
none of them resolve in the pipeline.

## 5. Canonical naming rules

Use:

- **"v7 five-class corpus"** for the represented document-class surface.
- **"five-class live Mailroom taxonomy"** for the current production taxonomy.
- **"class × subclass strata"** for the v7 stratification.
- **"correspondence intent"** for the intent dimension.
- **"27-key ground-truth schema"** for the current extraction/ground-truth field surface where that schema is being discussed.

Avoid:

- "v7 five-class taxonomy" — v7 is a corpus/schema revision, not the production taxonomy.
- "six-class live taxonomy" — the sixth class has been retired.
- "intent subclass" — conflates two label dimensions.
- "8-class v7 taxonomy" — the canonical eight-class language applies to the intent vocabulary used in correspondence backfill, not the document-class taxonomy.
- `compliance_filing` as a current pipeline class — it is retired.

## 6. Source-of-truth implementation

The implementation records the five represented Hub classes directly in `packages/llm-mailroom/src/pipeline/hf_corpora.py` via `HUB_CLASSES`.

The canonical operational pipeline diagram is `docs/assets/mailroom-pipeline.svg`. It now represents the live pipeline as a five-class taxonomy with no `compliance_filing` route.

Historical references to `compliance_filing` may remain in changelogs, archived fixtures, or migration history where they describe the former system. They are not current pipeline vocabulary.
