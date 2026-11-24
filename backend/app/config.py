"""Settings read from environment variables."""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Read settings such as ANTHROPIC_API_KEY from backend/.env when it exists,
# so the key doesn't have to be exported in every terminal window.
try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass
PROBLEMS_DIR = BACKEND_DIR / "problems"
DB_PATH = Path(os.getenv("COACH_DB", BACKEND_DIR / "coach.db"))

# COACH_FAKE_LLM=1 runs the whole app without an API key: canned assistant replies
# and placeholder scores. Useful for UI work and for tests.
FAKE_LLM = os.getenv("COACH_FAKE_LLM", "") == "1"
ASSISTANT_MODEL = os.getenv("COACH_ASSISTANT_MODEL", "claude-sonnet-5-5")
JUDGE_MODEL = os.getenv("COACH_JUDGE_MODEL", "claude-sonnet-5-5")

TIME_LIMIT_S = 45 * 60
PER_TEST_TIMEOUT_S = 2      # each test gets this long; optimal solutions finish well under it
MEMORY_LIMIT_MB = 512       # enforced on Linux; macOS ignores address-space limits
