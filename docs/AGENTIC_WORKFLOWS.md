# Agentic workflows

The first workflow is **Read-only investigation workflow** under Graph Intelligence. The user picks a published version and provides an anchor and question. The bounded workflow retrieves two hops, ranks candidates, and asks the opt-in provider for a cited answer. The UI displays the tool trace and supporting graph. PostgreSQL records a summary in existing query history. The workflow owns its tool sequence, and the provider only generates prose.

There are no background or write-capable agent tools in this milestone. Ontology approval, graph publication and purge continue through their existing authorized workflows. Planner-selected tools, durable execution logs, scheduled analysis and approval flows are separate future work.
