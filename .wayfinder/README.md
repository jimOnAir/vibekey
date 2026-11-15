# Wayfinder local-markdown tracker

Conventions for the map and its tickets in this repo. No native issue tracker is
wired up (see map Notes); these files are the canonical tracker state.

- **The map** is `map.md`, labelled `wayfinder:map`. It is an index: it gists and
  links decisions, never restates them.
- **Tickets** live in `tickets/NNNN-<slug>.md`, each a child of the map. The
  frontmatter `type` is the `wayfinder:<type>` label — one of `research`,
  `prototype`, `grilling`, `task`. Tickets carry no other labels.

## Wayfinding operations

- **Claim** a ticket by setting `assignee` to the dev driving the map, *before*
  any work. An open, unassigned ticket is unclaimed.
- **Blocking** (no native dependency links in local-markdown, so a body
  convention): the blocked ticket lists `blocked-by:` with sibling filenames.
  A ticket is unblocked when every ticket in its `blocked-by` list has
  `status: closed`.
- **Frontier query** — open, unclaimed, unblocked:

  ```bash
  cd .wayfinder/tickets && for f in *.md; do
    grep -q '^status: open' "$f" || continue
    grep -q '^assignee: \S' "$f" && continue
    grep -A9 '^blocked-by:' "$f" | grep -Eo '[0-9]{4}-[a-z0-9-]+\.md' |
      while read -r b; do grep -q '^status: closed' "$b" || echo "$f blocked-by $b"; done |
      grep -q . && continue
    echo "$f"
  done
  ```

- **Resolution**: record the answer as a `## Answer` section in the ticket, set
  `status: closed`, and append a one-line context pointer (name + link) to the
  map's **Decisions so far**. Assets created while resolving (prototypes,
  research findings) are linked from the ticket, not pasted in.
- **Research findings** are captured on a throwaway `research/<name>` branch —
  pushed, never merged, no PR. The ticket links the branch.
- **One ticket per session**, research tickets excepted.
