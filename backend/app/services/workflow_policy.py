"""Workflow policy shared by the stage catalogue and execution gates."""
from kg_pipeline.core.context import STAGES

GOVERNED = "governed"
VALIDATION_ONLY = "poc_validation_only"
POC_HIDDEN_STAGES = frozenset({6, 7, 9})
PREREQUISITES = {1: (), 2: (), 3: (2, 1), 4: (3,), 5: (3, 4), 6: (5,),
                 7: (5, 6), 8: (7,), 9: (8,), 10: (3, 9), 11: (10,),
                 12: (11,), 13: (12,), 14: (13,), 15: (14,), 16: (14, 15)}
POC_PREREQUISITES = {8: (5,), 10: (3, 8)}


def stage_enabled(policy, stage):
    return policy != VALIDATION_ONLY or stage not in POC_HIDDEN_STAGES


def prerequisites(policy, stage):
    if policy == VALIDATION_ONLY and stage in POC_PREREQUISITES:
        return POC_PREREQUISITES[stage]
    return PREREQUISITES[stage]


def active_stages(policy):
    return [{**stage, "prerequisites": prerequisites(policy, stage["no"])}
            for stage in STAGES if stage_enabled(policy, stage["no"])]
