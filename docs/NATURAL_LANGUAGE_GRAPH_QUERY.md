# Natural language to graph query

In **Graph Intelligence**, select a published version and choose **Natural language to Cypher**. Enter a question and request a draft. The API supplies the live graph's labels, relationship directions and property names to the configured provider. It validates the draft's structure and checks the pattern against the version schema.

Review or edit the proposed text, then explicitly run it. Execution uses the existing scoped compiler and read identity. The compiler accepts a labelled node or one typed directed relationship, declared variables or counts, and a bounded limit. The UI shows the result table and elapsed time. The Workbench remains the multi-format query tool. Query audit stores execution metadata. Unsupported questions return an error, and path or analytics questions can use their dedicated controls. The provider wrapper is replaceable; this deployment implements Groq.
