# Graph analytics

The existing **Graph Analytics** page shows version metrics, ranked nodes and communities from calculations saved at publication. It includes degree, betweenness, closeness, PageRank, connectivity, density and isolates under the existing size limits. Use the explorer's path controls for selected endpoints.

This upgrade adds bounded structural analysis to **Graph Intelligence**. It uses NetworkX over a two-hop sample from either workflow memory or the selected Neo4j version. Enter an anchor and optionally a target label. View candidate links, similar entities and the computed embedding, or download the result as JSON. A result flagged as truncated represents only a sample. Larger whole-graph algorithms, arbitrary filter configuration and execution history remain pending. The implementation avoids a GDS dependency and does not assert GDS availability.
