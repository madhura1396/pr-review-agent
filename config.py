import os

from dotenv import load_dotenv

load_dotenv()

# Groq retired llama-3.3-70b-versatile, the model this project was built on;
# requests for it now come back 404 model_not_found. Keeping the name in one
# place means the next retirement is a one-line change instead of a five-file
# hunt. Override with GROQ_MODEL to try a different model without editing code.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# The eval judge is deliberately a different model than the one under test.
# Scoring gpt-oss output with gpt-oss is self-grading, and a model tends to be
# lenient about its own work.
EVAL_JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", "qwen/qwen3.8-27b")
