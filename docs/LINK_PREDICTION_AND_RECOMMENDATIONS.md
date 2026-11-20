# Link prediction and recommendations

Open **Graph Intelligence**, set an anchor node and optionally a target label, then choose **Analyze neighborhood**. Jaccard overlap ranks two-hop candidates that are not direct neighbors in the retrieved undirected sample. Each candidate includes shared neighbor IDs. Recommendations average overlap and structural cosine similarity. A separate table shows cosine similarity. Scores are ranking signals rather than calibrated probabilities.

The implementation never creates predicted edges. Synthetic tests use a held-out relationship pattern to verify that the method recovers the two-hop candidate. Production quality evaluation, directional or typed prediction, a review-to-publication flow, rule configuration and historical tracking remain open.
