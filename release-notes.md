# Release Notes -- v0.19.0

> Released: 2026-11-25

FTreeKG 0.19.0 makes `ftreekg build` show what it is doing. A build over a
large tree used to print one line and then nothing for many minutes; it now
draws a progress bar for each pass. The release also brings the Art Techno
logo.

## What changed

**`ftreekg build` shows its progress.** Each pass draws a bar with elapsed
and remaining time: Scanning, Sizing files, Reading metadata and Embedding.
The case that prompted it was a tree over all of `~/repos`, about 471,000
nodes, which sat silent through embedding. In Python, `FileTreeKG.build()`
takes `progress=True` for the same bars and stays quiet by default.

**Embedding runs in chunks.** Texts go to the embedder 4,096 at a time so the
Embedding bar can move. The vectors are the same as before.

**An Art Techno logo.** The listing: a directory listing drawn as traces,
with the tagline EVERY FILE A NODE. The README shows the banner at the top,
by absolute URL so PyPI shows it too.

**The lock is current.** kgmodule-utils 0.32.0 and kg-rag 0.20.0.

## Upgrading

`pip install -U ftree-kg`. Existing graphs stay valid; no rebuild is needed.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
