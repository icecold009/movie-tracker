# Documentation verification record

Snapshot: `f2209af2891c9f5c9df3e03de8399419e2b51897`. Checks observed on 2026-10-03 in this isolated feature-branch copy.

| Acceptance check | Observed evidence |
| --- | --- |
| Source and diagram links | 20 case-study/diagram references resolve; 8 root-embedded diagram click targets checked. |
| Root diagram fidelity | Embedded Mermaid equals overview.mmd after adapting relative source URLs to the root README location. |
| Tracked-file accounting | 60 snapshot paths assigned exactly once; no missing or duplicate paths. |
| Detail graph structure | 9 functional groups have diagram nodes; no dangling endpoints. |
| Preview rendering | Overview and detail Mermaid rendered successfully; separate output PNG previews inspected previously. No new PNG is proposed for this repository. |
| Previously truncated source | 11 contiguous redacted fragments cover all lines of 4 previously truncated files; each was sent in a successful Jev helper call. |
| Application behavior | Application runtime was not exercised in this documentation task. |

These checks verify documentation structure and recorded review coverage. Inventory accounting does not establish every execution path, source conformance or hosted behavior. Fragment reviews retain their individual uncertainty; successful transmission is not approval. Jev thresholds remain unchanged. The exact source snapshot is now published; no PR, merge, application-code, dependency, schema or user-data change is included in this documentation update.

## Reproduce structural checks

With Node.js and Git installed, run from the repository root:

```sh
node docs/architecture/verify.mjs --self-test
```

The checker reads the explicitly pinned source snapshot, not the current HEAD, so a later documentation commit does not invalidate inventory accounting. It checks source paths, snapshot pinning, inventory equality, graph endpoints, Mermaid embed consistency and documentation links. Seven base structural failure cases cover inventory, paths, embeds, links and snapshot identity. The current checker has 10 intended-failure cases in total, including source-map checks; each must fail at its intended check. No files are changed by the checker. Node is an optional documentation-checking tool; this adds no application dependency.

This checker does not parse the full Mermaid language, verify arrow semantics, access hosted services or prove all application behavior. Rendering was checked separately. A passing structural check does not replace source-conformance review.

Rerun on 2026-10-04 passed for the pinned snapshot: 60 inventory paths, 36 documentation links, 25 diagram edges, 25 source-mapped arrows and 10 intended negative checks. This remains a read-only documentation-structure check, not semantic, runtime, hosted or renderer proof.

## Bounded source-claim review

On 2026-10-04, jev-1.13.0 evaluated four critical source-behavior claims against selected implementation files or exact contiguous source fragments from this snapshot. Observed call usage: 9900 input tokens and 179 output tokens. All four typed results selected supported.

| Claim | Typed result | Confidence |
| --- | --- | ---: |
| The Flask application checks session login and requires CSRF tokens for protected mutation routes. | supported | 1 |
| Database operations use direct psycopg2 PostgreSQL connections and transaction commit/rollback. | supported | 1 |
| Recommendation ranking uses deterministic feature scoring and filtering rather than an AI provider call. | supported | 1 |
| TMDB supplies external metadata/search behind a separately implemented client module. | supported | 1 |

Source evidence: [api/index.py](../../api/index.py), [database.py](../../database.py), [recommendations.py](../../recommendations.py), [tmdb.py](../../tmdb.py). Long-file fragments were reviewed with their original source path, commit and line ranges; this is bounded evidence, not a claim that every source file was supplied in one call.

These semantic checks supplement the structural checker. They cover only the four claims listed, not every diagram arrow or execution path, and do not replace complete-diff review. Branch synchronization is separate from PR review or merge; no merge is included here.

## Complete diagram relationship source map

Observed 2026-10-04: all **25 arrows** have latest supported Jev judgments (confidence 0.55–1.00), using pinned source f2209af2891c9f5c9df3e03de8399419e2b51897. Thirteen bounded calls used jev-1.13.0 with 41504 input/1318 output tokens. Four initially insufficient relationships were resolved by supplying their missing route, response-parsing and evaluation-call context. Each call supplied at most six redacted source excerpts of at most 10,000 characters. This does not approve the whole diff or prove hosted/runtime behavior.

Source corrections distinguish watchlist mutation guards from public usage-counter writes, remove the unsupported logger-to-database arrow, show metadata supplied to ranking through the route, and add direct browser poster requests to the image CDN. No application code, database, provider configuration or original checkout was changed.

### Source keys

- [S1](../../templates/index.html)
- [S2](../../api/index.py)
- [S3](../../database.py)
- [S4](../../tmdb.py)
- [S5](../../recommendations.py)
- [S6](../../observability.py)
- [S7](../../scripts/evaluate_recommender.py)
- [S8](../../vercel.json)
- [S9](../../tests/test_loading_ui.py)
- [S10](../../tests/test_app.py)
- [S11](../../templates/recommendations.html)

O/D mean overview/detail. Labels remain in the diagrams. S ranges are inclusive lines from the pinned Git snapshot. The checker validates exactly one map entry per arrow and source range bounds; ten intended-failure fixtures include missing mapping, unknown source key and invalid line range. It does not evaluate source semantics.

| Arrow | Source ranges | Supported confidence |
| --- | --- | ---: |
| O B --> F | S1:1-24, S2:291-313 | 0.91 |
| O F --> S | S2:379-388, S2:451-476, S2:82-87 | 0.98 |
| O S --> D | S2:379-388, S2:405-448, S2:451-470 | 0.96 |
| O F --> D | S2:291-313, S2:60-71, S3:108-129 | 1 |
| O D <--> P | S3:20-65, S3:108-129 | 0.86 |
| O F --> T | S2:256-289, S2:316-328 | 0.98 |
| O T -.-> X | S4:13-22, S4:76-100 | 0.96 |
| O X -.-> T | S4:86-127, S4:128-189, S4:191-243 | 0.96 |
| O F --> R | S2:256-289 | 0.94 |
| O R --> F | S5:172-198, S2:270-289 | 0.99 |
| D UI --> API | S1:1-24, S1:74-98, S2:330-388, S2:291-313 | 0.84 |
| D AUTH --> API | S2:28-43, S2:74-87, S2:379-388 | 0.82 |
| D API --> DB | S2:291-313, S2:60-71, S3:108-129 | 1 |
| D API --> META | S2:256-289, S2:316-328 | 0.98 |
| D API --> RANK | S2:256-289, S5:172-198 | 0.99 |
| D DB --> RANK | S2:256-289, S5:172-198 | 0.83 |
| D META --> RANK | S2:24-26, S2:256-289, S4:191-243, S5:172-198 | 0.7 |
| D API --> OBS | S2:60-71, S6:1-22 | 0.92 |
| D EVAL .-> RANK | S7:18-30, S7:242-255, S5:209-222 | 0.55 |
| D RUN .-> API | S8:1-15 | 0.88 |
| D API --> RECOVERY | S2:163-218 | 0.99 |
| D RECOVERY --> UI | S2:291-313, S1:74-98 | 0.99 |
| D SUPPORT .-> UI | S9:1-65, S10:1-12 | 0.78 |
| O B .-> X | S1:212-220, S4:156-184 | 0.96 |
| D UI .-> IMAGES | S1:212-220, S11:69-78, S4:220-243 | 0.99 |
