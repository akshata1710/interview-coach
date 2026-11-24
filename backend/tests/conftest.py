import os
import tempfile

# must be set before the app module is imported
os.environ["COACH_FAKE_LLM"] = "1"
os.environ["COACH_DB"] = os.path.join(tempfile.mkdtemp(prefix="coach-test-"), "test.db")
