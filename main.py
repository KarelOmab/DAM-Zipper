from flask import Flask, request, jsonify, g
import sqlite3
import os
import zipfile
from werkzeug.utils import secure_filename
import shutil
import threading
import time
import json

app = Flask(__name__)

DEBUG = True

# Database configuration
DATABASE = 'data.db'

# Database helper functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Logger class
class Logger:

    def __init__(self):
        self.job_id = None

    def log_request(self, source_ip=None, user_agent=None, method=None, request_url=None, response_status=None):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO requests (source_ip, user_agent, method, request_url, response_status) 
            VALUES (?, ?, ?, ?, ?)
            """, (source_ip, user_agent, method, request_url, response_status))
        db.commit()
        return cursor.lastrowid  # Return the ID of the inserted request
    
    def create_job_record(self, request_id, message):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO jobs (request_id, message, status) 
            VALUES (?, ?, 'pending')
            """, (request_id, message))
        db.commit()
        return cursor.lastrowid  # Return the ID of the inserted job

    def log_job(self, job_id, message):
        db = get_db()
        with db:
            db.execute("""
                INSERT INTO events (job_id, message) 
                VALUES (?, ?)
                """, (job_id, message))
            db.commit()

# Job class
class Job:
    def __init__(self, request_data, file_ops, operation_profile):
        self.request_data = request_data
        self.file_ops = file_ops
        self.operation_profile = operation_profile

class FileOps:
    def __init__(self, operation_profile, logger, job_id):
        self.operation_profile = operation_profile
        self.temp_job_directory = os.path.join(os.getcwd(), 'temp')
        self.logger = logger
        self.job_id = job_id

    def download(self, file_map):
        for remote_file, local_name in file_map.items():
            try:
                # Split the local name into directory and filename
                local_dir, filename = os.path.split(local_name)
                local_dir_path = os.path.join(self.temp_job_directory, local_dir)
                if not os.path.exists(local_dir_path):
                    os.makedirs(local_dir_path)  # Create any necessary directories

                # Continue with previous logic
                source_file_path = os.path.join(self.operation_profile.download_path, remote_file)
                destination_file_path = os.path.join(local_dir_path, secure_filename(filename))
                shutil.copy2(source_file_path, destination_file_path)

                if DEBUG:
                    print(f"Downloaded {source_file_path} to {destination_file_path}")

                self.logger.log_job(self.job_id, f"Downloaded {source_file_path} to {destination_file_path}")
            except Exception as e:

                if DEBUG:
                    print(f"Failed to download {source_file_path}: {e}")

                self.logger.log_job(self.job_id, f"Failed to download {source_file_path}: {e}")

    def zip(self, zip_name):
        zip_dir = os.path.join(self.operation_profile.zip_path)
        zip_path = os.path.join(zip_dir, secure_filename(zip_name) + '.zip')
        
        if not os.path.exists(zip_dir):
            os.makedirs(zip_dir)

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.temp_job_directory, topdown=True):
                    print(f"Zipping: Current directory: {root}")  # Debug print
                    dirs[:] = [d for d in dirs if os.path.join(root, d) != zip_dir]
                    for file in files:
                        if file == '.DS_Store' or file == os.path.basename(zip_path):
                            continue
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start=self.temp_job_directory)
                        zipf.write(file_path, arcname)
                        print(f"Added {file_path} to zip as {arcname}")  # Debug print

                print(f"Zipping completed: {zip_path}")  # Debug print
                self.logger.log_job(self.job_id, f"Zipping completed: {zip_path}")

        except Exception as e:
            print(f"Exception during zipping: {e}")
            return None
        return zip_path


    def upload(self, zip_path):
        try:
            # Placeholder for actual upload logic
            self.logger.log_job(self.job_id,f"Uploaded {zip_path} to {self.operation_profile.upload_path}")
        except Exception as e:
            self.logger.log_job(self.job_id,f"Failed to upload {zip_path}: {e}")

# OperationProfile class
class OperationProfile:
    # Placeholder for actual server profile logic
    def __init__(self, profile_name):
        self.profile_name = profile_name
        self.download_path = os.path.join(os.getcwd(), 'sample_files')
        self.zip_path = os.path.join(os.getcwd(), 'temp')
        self.upload_path = '/dummy/path/for/upload/'  # Example upload path


# Job Submission Endpoint
@app.route('/submit_job', methods=['POST'])
def submit_job():
    payload = request.json  # or however you extract your job payload
    payload_message = json.dumps(payload)  # Convert payload to a JSON string

    logger = Logger()
    # Log the request and get the ID
    request_id = logger.log_request(
        source_ip=request.remote_addr, 
        user_agent=request.headers.get('User-Agent'),
        method=request.method,
        request_url=request.path,
        response_status=201  # Assume success for this example
    )

    if request_id:
        # Create a new job record
        job_id = logger.create_job_record(request_id, payload_message)
        return jsonify({'message': 'Job submitted successfully', 'job_id': job_id}), 201
    else:
        return jsonify({'message': 'Error occurred during job submission'}), 400




def job_processor():
    with app.app_context():  # Create an application context
        while True:
            db = get_db()
            with db:
                # Fetch the next pending job
                job = db.execute('''
                    SELECT id, message FROM jobs WHERE status = 'pending'
                    ORDER BY id ASC
                    LIMIT 1
                ''').fetchone()

                if job:
                    job_id, job_payload = job
                    logger = Logger()
                    payload = json.loads(job_payload)
                    files = payload.get('files', {})
                    server = payload.get('server', 'default_profile')
                    token = payload.get('token', 'default_zip_name')

                    # Update job status to 'in progress' and record start time
                    db.execute('''
                        UPDATE jobs SET status = 'in progress', start_time = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (job_id,))

                    try:
                        # Process the job
                        operation_profile = OperationProfile(server)
                        file_ops = FileOps(operation_profile, logger, job_id)

                        file_ops.download(files)
                        zip_path = file_ops.zip(token)
                        file_ops.upload(zip_path)

                        # Update job status to 'completed' and record end time
                        db.execute('''
                            UPDATE jobs SET status = 'completed', end_time = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (job_id,))
                    except Exception as e:
                        # In case of error, log and update job status
                        print("EXCEPTION", e)
                        db.execute('''
                            UPDATE jobs SET status = 'failed', end_time = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (job_id,))

            if DEBUG:
                print("Sleeping...zzzZZZZzzzz")

            time.sleep(10)  # Check for new jobs every 10 seconds



# Start the job processor thread
job_processor_thread = threading.Thread(target=job_processor, daemon=True)
job_processor_thread.start()

if __name__ == '__main__':
    init_db()  # Make sure to initialize the database
    app.run(debug=DEBUG)
