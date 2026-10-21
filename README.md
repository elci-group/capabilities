# ELCI Capability Registry

Canonical capability registry for the ELCI Group (ELCI-RGCA-001 §11/§30).

Every active ELCI repository declares a machine-readable manifest at
`.elci/project.toml`. This repository aggregates those manifests into a
normalized capability graph:

| Artifact | Contents |
|---|---|
| `generated/projects.json` | every registered project: class, status, maturity, authority, lifecycle |
| `generated/capabilities.json` | capability → providers / consumers |
| `generated/dependency-graph.json` | typed edges (`controls`, and later `depends_on`, `consumes`, `observes`, `stores_in`, …) |
| `generated/architecture.mmd` | generated Mermaid architecture diagram — **the machine graph wins** over any hand-drawn diagram (§30) |

## Regenerate

```sh
bin/compile.py            # reads .elci/project.toml under /home/sal and /tmp/kilo/clones
```

Set `ELCI_REPOS_ROOT` to point at a different estate root.

## Capability identifiers

Capability ids are globally stable and brand-free (§11):

```text
elci.repository.drift          elci.repository.versioning
elci.storage.ontology          elci.dependency.reduce
elci.context.bundle            elci.inference.route
```

Brand names (Azusa, Kaptaind, Padagonia, …) name the **providers** of these
capabilities, never the contract — implementations may change without
changing the vocabulary.

## Agent discovery contract (§12)

Agents SHOULD resolve capabilities deterministically:

```text
required: elci.repository.drift  →  provider: azusa (cli, rust) — active/beta
```

Lookup = read `generated/capabilities.json`. Do not guess from names.

## Governance

- The registry NEVER contains secrets, tokens, or private endpoints (§34).
- Manifest validation errors are reported in the compiler output, never
  silently defaulted (§5, §29).
- CI validation (`elci-check`) lands with ELCI-RGCA-001 Phase 6.
