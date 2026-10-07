"""Plant growth rule, shared by the entries and plant handlers.

Every 20 check-ins grows the plant one stage. Keep in sync with
STAGE_THRESHOLDS in src/App.jsx.
"""

PLANT_STAGE_THRESHOLDS = [
    (80, 'mature_tree'),
    (60, 'young_tree'),
    (40, 'plant'),
    (20, 'seedling'),
]


def plant_stage(total):
    """Return the plant stage for a number of check-ins."""
    for threshold, stage in PLANT_STAGE_THRESHOLDS:
        if total >= threshold:
            return stage
    return 'sprout'
