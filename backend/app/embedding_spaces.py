"""Model-vector compatibility is independent of detector/crop provenance."""

LEGACY_REAL_SPACE = 'poseswin-test-on-2020-v1'
CURRENT_REAL_SPACE = 'poseswin-katmai-6y-v1'


def for_pipeline(pipeline):
    return pipeline if pipeline.startswith('mock') else CURRENT_REAL_SPACE
