# Real insurance-claim sample documents (PDF)

Eight real documents from the published `insurance_claim` corpus of
[`Lucius-Morningstar/mailroom-dataset`](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset)
(two per health stratum this package produces: carrier, inpatient,
outpatient, pde), rendered as faithful A4 PDFs.

- Every PDF is a byte-faithful type-set of the corpus row's verbatim
  `doc_text` — the same document text `scripts/render_eob.py` produces and
  the pipeline evaluates against.
- Content carries no real PHI: the corpus is CMS DE-SynPUF (synthetic
  beneficiaries, deterministic pseudonyms).
- Deterministic regeneration: `python scripts/render_samples.py --input <ground_truth_hardened.jsonl>`
  (`--seed 42`, two per stratum) reproduces these exact bytes — see
  `manifest.json` for per-file sha256.

| Stratum | Files |
|---|---|
| carrier | `sample_carrier_887043388115026.pdf`, `sample_carrier_887223387326780.pdf` |
| inpatient | `sample_inpatient_196501176992480_1.pdf`, `sample_inpatient_196591176969302_1.pdf` |
| outpatient | `sample_outpatient_542332281132315_1.pdf`, `sample_outpatient_542452281547033_1.pdf` |
| pde | `sample_pde_233204489280799.pdf`, `sample_pde_233444490300134.pdf` |

Source rows: `ground_truth_hardened.jsonl` — the **v9 corpus**
(`Lucius-Morningstar/mailroom-dataset`, 3,302 rows; the frozen v8
`mailroom-corpus` 2,000-row baseline is its lineage parent). Samples here
cover the four health strata native to this package's SynPUF pipeline dump
(property/auto also ship in the corpus).