"""One module per pipeline stage. Each exposes a `run(ctx, ...)` function that reads
earlier results from the PipelineContext, does its work, writes its output back
to the context and logs what happened."""
