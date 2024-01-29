from app import app, init_db, start_job_processor_thread
import os

if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    start_job_processor_thread()

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0")
