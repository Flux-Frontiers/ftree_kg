# FileTreeKG Analysis

## Summary

| Metric | Value |
|--------|-------|
| Total paths | 1,565 |
| Total links | 1,565 |
| Files | 1,366 |
| Directories | 199 |
| Symlinks | 0 |
| Total size (files) | 8.0 MB |

## Size by top-level directory

```
.agentkg             ████████████████████      4.0 MB
.claude              ███████████████░░░░░      3.0 MB
.pycodekg            ████░░░░░░░░░░░░░░░░    969.0 KB
.                    █░░░░░░░░░░░░░░░░░░░    371.0 KB
src                  ░░░░░░░░░░░░░░░░░░░░     65.0 KB
analysis             ░░░░░░░░░░░░░░░░░░░░     17.0 KB
tests                ░░░░░░░░░░░░░░░░░░░░      6.0 KB
docs                 ░░░░░░░░░░░░░░░░░░░░      6.0 KB
scripts              ░░░░░░░░░░░░░░░░░░░░      2.0 KB
examples             ░░░░░░░░░░░░░░░░░░░░      1.0 KB
```

## Directory tree (depth ≤ 3)

```
├── .agentkg/
│   ├── graph.sqlite
│   ├── lancedb/
│   │   └── nodes.lance/
│   └── snapshots/
│       ├── 20260406T211833.json
│       ├── 20260406T211959.json
│       ├── 20260406T212051.json
│       ├── 20260406T214011.json
│       ├── 20260406T214048.json
│       ├── 20260406T214248.json
│       ├── 20260406T214650.json
│       ├── 20260406T214737.json
│       ├── 20260406T215059.json
│       ├── 20260406T215142.json
│       ├── 20260406T215319.json
│       ├── 20260406T221002.json
│       └── … (5 more)
├── .claude/
│   ├── CLAUDE.md
│   ├── agents/
│   ├── commands/
│   │   ├── bump.md
│   │   ├── changelog-commit.md
│   │   ├── codekg.md
│   │   ├── continue.md
│   │   ├── knowledge-copilot.md
│   │   ├── protocol.md
│   │   ├── release.md
│   │   ├── setup-codekg-mcp.md
│   │   ├── setup-copilot.md
│   │   ├── setup-mcp.md
│   │   ├── setup-project.md
│   │   ├── update-copilot.md
│   │   └── … (1 more)
│   ├── plugins/
│   │   ├── blocklist.json
│   │   ├── blocklist.json.cae85a49aa0582b2.tmp
│   │   ├── install-counts-cache.json
│   │   ├── installed_plugins.json
│   │   ├── known_marketplaces.json
│   │   └── marketplaces/
│   ├── settings.local.json
│   └── skills/
│       ├── codekg/
│       ├── codekg-thorough-analysis.md
│       ├── dockg/
│       ├── documentation-lookup/
│       ├── kgrag/
│       ├── kgrag-usage/
│       ├── kgrag-usage.skill
│       ├── new-kg-module/
│       ├── new-kg-module.skill
│       ├── publish/
│       └── skill-creator/
├── .mcp.json
├── .pre-commit-config.yaml
├── .pycodekg/
│   ├── graph.sqlite
│   ├── lancedb/
│   │   └── pycodekg_nodes.lance/
│   └── snapshots/
│       ├── 098fda4eb0a656529747f6d5b66be56aa2777602.json
│       ├── 1324e876992131002e459ec4e216b611271f5f2d.json
│       ├── 2bf7bb60f4a587a1ce82745b84179a5d957ccb67.json
│       ├── 8aab203f66f8fe3afc33b342bc3bcf69eb218989.json
│       ├── 9f9d89d5136486603b01845026b953cada123794.json
│       ├── b6560dbc3c0e048767e1fdfc25beaaa1a564a20b.json
│       ├── e5a9347ec43628e3bddec96622a4d9f8e9d393c7.json
│       ├── eb73eca9f211cec1deb14ae521491bb8a4406762.json
│       ├── f878663a292cc691296f88b5b78a12d71e37dd48.json
│       └── manifest.json
├── .secrets.baseline
├── CHANGELOG.md
├── FTreeKG.code-workspace
├── LICENSE
├── Makefile
├── README.md
├── analysis/
│   ├── FTreeKG_analysis_20260321.md
│   └── filetreekg_analysis.md
└── … (14 more)
```

## Path breakdown

| Kind | Count |
|------|-------|
| `directory` | 199 |
| `file` | 1,366 |

## Link breakdown

| Relation | Count |
|----------|-------|
| `CONTAINS` | 1,565 |
