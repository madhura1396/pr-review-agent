import os

# DeepEval phones home on import unless this is set. Do it here so it is in
# place before any test module imports deepeval.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
