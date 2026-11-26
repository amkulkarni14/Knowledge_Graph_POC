# Durable workspace recovery

Use the existing owner-scoped SQLite library. Lazily create an additive workspace_recovery table with versioned JSON checkpoints keyed by workspace UUID. Existing workspace, domain and artifact rows stay in place. Deploy only after a backup and explicit approval for any migration with data risk. Phase 1 keeps the single API worker model.

An explicit authenticated reopen endpoint restores typed scope, catalog, draft, evidence and validation metadata. Hash captured inputs and validate referenced snapshot artifacts before offering recovery. List durable entries without loading graphs. Reopen does not replay jobs or reconnect. Source recovery records connector/asset hints and requires fresh authorization and connection selection. There is no existing external credential-reference resolver, so credentials and connection objects are excluded. Staged rows and unsaved graphs are not restored as executable state. Historical completed stages remain visible separately. Saved snapshots remain readable by owner even when the source must reconnect. Reconnecting invalidates source-dependent execution state; preserve the saved draft for rechecking against the new catalog.

SQLite writes are transactional. Interrupted jobs become interrupted rather than resubmitted. The existing active-session API retains its semantics; add a durable workspace list and explicit reopen. Existing library records without checkpoints may recover checked artifacts but cannot establish missing stage evidence. Explicit workspace reset archives the durable list entry without deleting saved drafts or snapshots. No storage schema change is applied to the live environment in development.

## API and operator verification

- `GET /api/v1/workspaces` lists active and inactive workspaces owned by the authenticated account.
- `POST /api/v1/workspaces/{id}/reopen` restores an owned workspace or returns its current active state. No job is scheduled. Live stage APIs keep their existing session routes.
- Session views expose the last update, selected domain, saved build configuration, snapshot identifiers, historical completion, recovery warnings and reconnection status. Historical stage IDs are evidence. Execution gates use the restored runnable stages.
- Legacy records can reopen a single saved draft and a readable current snapshot. Files with ambiguous draft choices are preserved. Governed workspaces require review and approval again. An uploaded file or connector must be reselected if no authorized live connection exists.
- Checkpoints retain source type and selected asset identifiers. Credential references are empty until a secure resolver exists. Extraction, cleaning data and unsnapshotted graphs require a rebuild; previously saved versioned snapshots are loaded on demand.

On a disposable deployment, create a workspace, connect a source and save scope, ontology, validation and a graph snapshot. Restart only that test backend. Sign in as the same owner, open the workspace from Home, inspect Last Completed Stage and Open saved graph, then use Reconnect source to resume building. Repeat Open workspace and confirm the job count and snapshot list do not change. Verify another account receives 404 on the reopen and snapshot APIs. Before any real deployment, back up the backend volume and confirm operator approval for the deployment.
