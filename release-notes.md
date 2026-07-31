# Release Notes — v0.10.0

> Released: 2026-07-31

FTreeKG 0.10.0 is a security release. Nothing under `src/` changed behaviour, but every
install of 0.9.0 and earlier pulled a `transformers` version exposed to two high-severity
advisories, and the only way to clear them is a dependency floor lift that upgrades
transformers from 4.x to 5.x. That upgrade is why this is a minor rather than a patch.

## What changed

**Two high-severity transformers advisories, closed.** FTreeKG declares
`kgmodule-utils[semantic,sqlite-vec]` as a core runtime dependency, and kgmodule-utils used
to cap `transformers` at `<4.57`. That cap held every FTreeKG install at transformers 4.56.2
— exposed to a remote-code-execution advisory fixed in 5.3.0, and to an arbitrary-code-execution
flaw in the LightGlue model-loading path fixed in 5.5.0. kgmodule-utils 0.9.0 replaced the cap
with `>=5.5.0,<6`; lifting our floor to `>=0.9.0` is what actually delivers the fix to anyone
installing this package.

**Your index does not need rebuilding.** The transformers major bump sounds like it should
invalidate embeddings, and it does not. Upstream verified that embedding output is bitwise
identical across the 4.x → 5.x boundary on bge-small, bge-large, and nomic-embed — including
empty, unicode, and CRLF inputs — that a full index rebuild is byte-identical, and that
queries against a 4.x-built index return identical rankings. The full FTreeKG suite, real
embedder included, passes on transformers 5.14.1.

**The `kgdeps` extra sheds lancedb.** `doc-kg` moves to `>=0.20.0` and `pycode-kg` to
`>=0.21.2`. Both siblings dropped lancedb from their published wheels over that range, so the
optional KG integration path no longer drags a vector database FTreeKG stopped using in 0.9.0.

**`ftree_kg.__version__` was lying.** It sat at 0.9.0 while `pyproject` moved, and it is
exported from the package root, so anything reading `ftree_kg.__version__` got a stale answer.
The CLI was never affected — `ftreekg --version` and `ftreekg status` both read installed
package metadata. Now bumped in step with everything else.

**Citation and README fixes.** The APA and BibTeX blocks carried
`10.5281/zenodo.1182124358` as a DOI. That number is the GitHub repository id — correct inside
the Zenodo badge URL, wrong as a DOI, and it returned 404 for anyone who tried to cite
FTreeKG. It is now the concept DOI `10.5281/zenodo.19742541`, which tracks the latest deposit
rather than pinning one snapshot. Alongside it: `CITATION.cff` gained its missing `doi` field
and a corrected `date-released`, and four README links that pointed at a non-canonical repo
name now point at `ftree_kg`.

## Upgrading

`pip install --upgrade ftree-kg`. There is no migration and no re-index.

The one thing to know is that transformers will move from 4.x to 5.x in your environment. If
you have other packages pinned to transformers 4, resolve that before upgrading — FTreeKG
cannot stay on 4.x without reintroducing both advisories.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
