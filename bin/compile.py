#!/usr/bin/env python3
"""ELCI portfolio compiler (ELCI-RGCA-001 §30).
Aggregates .elci/project.toml manifests into machine-readable portfolio artifacts.
Manifest roots are searched under: $ELCI_REPOS_ROOT (default /home/sal) and
/tmp/kilo/clones. Unknown fields are tolerated (§5); required fields that are
missing are reported, never silently defaulted."""
import json, os, sys, glob
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOTS = [os.environ.get("ELCI_REPOS_ROOT", "/home/sal"), "/tmp/kilo/clones"]
out_dir = os.environ.get("ELCI_GENERATED", os.path.join(os.path.dirname(__file__), "..", "generated"))

projects, errors = [], []
seen = set()
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for mf in glob.glob(os.path.join(root, "*", ".elci", "project.toml")):
        name = mf.split(os.sep)[-3]
        if name in seen:
            continue
        seen.add(name)
        try:
            with open(mf, "rb") as f:
                t = tomllib.load(f)
            p = t.get("project", {})
            missing = [k for k in ("id", "descriptor", "status", "maturity", "class") if k not in p]
            if missing:
                errors.append({"repo": name, "error": f"missing required fields: {missing}"})
                continue
            arch = t.get("architecture", {})
            projects.append({
                "id": p["id"], "name": p.get("name", p["id"]),
                "descriptor": p["descriptor"], "status": p["status"],
                "maturity": p["maturity"], "class": p["class"],
                "organisation": t.get("ownership", {}).get("organisation", "elci-group"),
                "independent_boundary": arch.get("independent_boundary"),
                "boundary_reason": arch.get("boundary_reason"),
                "parent": arch.get("parent", []),
                "capabilities": arch.get("capabilities", []),
                "consumers": arch.get("consumers", []),
                "authority": t.get("authority", {}),
                "lifecycle": t.get("lifecycle", {}),
                "manifest": os.path.relpath(mf, root),
            })
        except Exception as e:
            errors.append({"repo": name, "error": str(e)[:200]})

projects.sort(key=lambda p: p["id"])

# capability graph (§11): globally stable ids; brand names are not the contract
caps = {}
for p in projects:
    for cap in p["capabilities"]:
        caps.setdefault(cap, {"capability": cap, "providers": [], "consumers": []})
        caps[cap]["providers"].append(p["id"])
for p in projects:
    for cap in p["consumers"]:
        caps.setdefault(cap, {"capability": cap, "providers": [], "consumers": []})
        caps[cap]["consumers"].append(p["id"])

# dependency graph (§13): typed edges
edges = []
for p in projects:
    parent = p.get("parent")
    if isinstance(parent, str):
        edges.append({"from": parent, "to": p["id"], "type": "controls"})
    elif isinstance(parent, list):
        for q in parent:
            edges.append({"from": q, "to": p["id"], "type": "controls"})

# architecture diagram (§30): Mermaid, observation/reasoning/actuation planes
planes = {"platform": "PLATFORM", "observation": "OBSERVATION", "reasoning": "REASONING",
          "orchestration": "ACTUATION", "actuation": "ACTUATION", "storage": "SHARED INFRASTRUCTURE",
          "transport": "SHARED INFRASTRUCTURE", "inference": "REASONING",
          "runtime": "HOST/RUNTIME", "developer-tool": "DEVELOPER TOOLS",
          "library": "LIBRARIES", "protocol": "PROTOCOLS", "research": "RESEARCH",
          "experiment": "EXPERIMENTS", "support": "SUPPORT", "legacy": "LEGACY"}
mermaid = ["graph TD"]
for p in projects:
    mermaid.append(f'  {p["id"].replace("-", "_")}["{p["id"]}"]')
groups = {}
for p in projects:
    groups.setdefault(planes.get(p["class"], "OTHER"), []).append(p["id"].replace("-", "_"))
mermaid.append("  subgraph PLANES")
for plane, ids in groups.items():
    safe = plane.replace("/", "_").replace(" ", "_")
    mermaid.append(f"    subgraph {safe}")
    for i in ids:
        mermaid.append(f"      {i}")
    mermaid.append("    end")
mermaid.append("  end")

os.makedirs(out_dir, exist_ok=True)
artifacts = {
    "projects.json": {"schema": "elci.portfolio/v1", "count": len(projects), "projects": projects},
    "capabilities.json": {"schema": "elci.capabilities/v1", "count": len(caps), "capabilities": sorted(caps.values(), key=lambda c: c["capability"])},
    "dependency-graph.json": {"schema": "elci.graph/v1", "nodes": [p["id"] for p in projects], "edges": edges},
    "architecture.mmd": "\n".join(mermaid) + "\n",
}
for fname, data in artifacts.items():
    with open(os.path.join(out_dir, fname), "w") as f:
        if fname.endswith(".json"):
            json.dump(data, f, indent=2)
        else:
            f.write(data)

print(json.dumps({"projects": len(projects), "capabilities": len(caps), "edges": len(edges), "errors": errors[:10], "manifest_roots": ROOTS}))
