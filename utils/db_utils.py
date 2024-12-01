import duckdb
import shortuuid  # replaces uuid
from typing import Optional, List, Dict
import json
from datetime import datetime


class AgentRunsDB:
    def __init__(self, db_file: str = "agent_runs.db"):
        self.conn = duckdb.connect(db_file)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            start_timestamp TEXT,
            updated_timestamp TEXT
        )
        """)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS steps (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            timestamp TEXT,
            output TEXT,
            handoff_msg TEXT,
            actor_agent TEXT,
            target_agent TEXT,
            summary TEXT,
            tool_call_id TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        )
        """)

    # Create a new run
    def create_run(self) -> str:
        run_id = shortuuid.uuid()[:8]  # Generate shorter ID (8 chars)
        timestamp = datetime.utcnow().isoformat()
        self.conn.execute("""
        INSERT INTO runs (id, start_timestamp, updated_timestamp) VALUES (?, ?, ?)
        """, (run_id, timestamp, timestamp))
        return run_id

    # Update a run's timestamp
    def update_run_timestamp(self, run_id: str):
        timestamp = datetime.utcnow().isoformat()
        self.conn.execute("""
        UPDATE runs SET updated_timestamp = ? WHERE id = ?
        """, (timestamp, run_id))

    # Add a step to a run
    def add_step(self, run_id: str, output: str, handoff_msg: str, actor_agent: str,
                 target_agent: str, summary: str, tool_call_id: str) -> str:
        step_id = shortuuid.uuid()[:8]  # Generate shorter ID (8 chars)
        timestamp = datetime.utcnow().isoformat()
        self.conn.execute("""
        INSERT INTO steps (id, run_id, timestamp, output, handoff_msg, actor_agent, target_agent, summary, tool_call_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (step_id, run_id, timestamp, output, handoff_msg, actor_agent, target_agent, summary, tool_call_id))
        self.update_run_timestamp(run_id)
        return step_id

    # Get all runs
    def get_all_runs(self) -> List[Dict]:
        results = self.conn.execute("SELECT * FROM runs").fetchall()
        return [{"id": row[0], "start_timestamp": row[1], "updated_timestamp": row[2]} for row in results]

    # Get all steps for a run
    def get_steps_for_run(self, run_id: str) -> List[Dict]:
        results = self.conn.execute("""
        SELECT * FROM steps WHERE run_id = ?
        """, (run_id,)).fetchall()
        return [
            {
                "id": row[0],
                "run_id": row[1],
                "timestamp": row[2],
                "output": row[3],
                "handoff_msg": row[4],
                "actor_agent": row[5],
                "target_agent": row[6],
                "summary": row[7],
                "tool_call_id": row[8],
            } for row in results
        ]

    # Clear the database (useful for testing)
    def clear_database(self):
        self.conn.execute("DELETE FROM steps")
        self.conn.execute("DELETE FROM runs")


# Example Usage
if __name__ == "__main__":
    db = AgentRunsDB()

    # Create a new run
    run_id = db.create_run()
    print(f"New run created with ID: {run_id}")  # Will print something like "3k4j5n2m"

    # Add steps to the run
    step_id = db.add_step(
        run_id=run_id,
        output="Completed task A",
        handoff_msg="Passing to agent B",
        actor_agent="AgentA",
        target_agent="AgentB",
        summary="Summary of step A",
        tool_call_id="tool-1234"
    )
    print(f"Step added with ID: {step_id}")  # Will print something like "7h8j9k2l"

    # Fetch all runs
    runs = db.get_all_runs()
    print("All runs:", json.dumps(runs, indent=2))

    # Fetch all steps for a run
    steps = db.get_steps_for_run(run_id)
    print(f"Steps for run {run_id}:", json.dumps(steps, indent=2))