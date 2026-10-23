# DMR-093 non-core feeder preservation

Published 2026-10-23T02:33:41.738104+00:00. The user excluded full Enron/claims audits and prioritized feature-branch preservation. These full-checkout branches preserve the existing hub package trees without changing their independent repositories.

Both branches point to `59c879d9fb4480084e53137e2e9fb25650933944`, the reviewed reconciliation checkout before subsequent core-only imports. Final PR162 must retain these exact feeder trees; preservation does not depend on unrelated core commits sharing the same root SHA.

- [feature/enron-evaluation-environment](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/enron-evaluation-environment): `Enron-Evaluation-Environment`, 86 tracked paths, Git tree `effdb3dc754df39cae9442780f7f719fe9786430`.
- [feature/claims-data-eda](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/tree/feature/claims-data-eda): `claims-data-eda`, 63 tracked paths, Git tree `3cc27d0b3ca4b0a3685866e6768c866245f76b14`.

Remote refs were independently read after creation and matched the requested commit. Inventories include every tracked blob and mode. No ref was force-updated. Existing `feature/agent-mailroom` and recovery tags remain intact.

Pruning belongs in a separate PR dependent on #162. GitHub #163 is the closed rollback-release issue; it cannot be reused as a PR number. [PR167](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/167) removes only these two active package roots and wiring while retaining the five core packages, historical evidence, standalone links, taxonomy and centralized corpus helpers.

The five-core branch retains all 26 count-neutral committed persona mirrors.
The eight global canonical profiles already differed from the committed
project copies before this card; none contains a current seven-package count.
No unrelated global profile configuration was overwritten. Global/profile
byte-parity drift is pre-existing and is not claimed repaired by this pruning.
