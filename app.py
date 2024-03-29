from flask import Flask, request, jsonify, g
from config import DATABASE, DEBUG, PROFILE_DIR
import sqlite3
import os
import zipfile
from werkzeug.utils import secure_filename
import subprocess
import threading
import time
import json
import tempfile
from dotenv import load_dotenv
import hashlib

# Globals
app = Flask(__name__)

# Load the .env file
load_dotenv()

path_profiles = os.path.join(os.getcwd(), PROFILE_DIR)

def get_operation_profile_by_name(name):
    for root, _, files in os.walk(path_profiles):
        for file in files:
            if file.endswith(".txt"):
                # Read the file and fetch the key-value pair
                with open(os.path.join(root, file), 'r') as file:

                    op_name, op_path_up, op_path_down = None, None, None

                    for line in file:
                        key, value = line.strip().split('=')

                        if key == "NAME":
                            op_name = value
                        elif key == "PATH_DOWN":
                            op_path_down = value
                        elif key == "PATH_UP":
                            op_path_up = value
                    
                    if op_name == name:
                        if op_path_up and op_path_down:
                            return OperationProfile(op_name, op_path_down, op_path_up)
    return None

def get_db():
    try:
        if 'db' not in g:
            g.db = sqlite3.connect(DATABASE)
            g.db.row_factory = sqlite3.Row
        return g.db
    except sqlite3.Error as e:
        # Handle the error or log it
        print(f"Database error: {e}")
        return None

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# Logger class
class Logger:

    # Make sure Logger is initialized only once
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.job_id = None

    def log(self, message):
        print(f"LOGGER:", {message})

    def log_error(self, message):
        # Log error messages
        print(f"ERROR: {message}")  # Or use a more sophisticated logging mechanism

    def log_request(self, source_ip=None, user_agent=None, method=None, request_url=None, request_raw=None):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO requests (source_ip, user_agent, method, request_url, request_raw) 
            VALUES (?, ?, ?, ?, ?)
            """, (source_ip, user_agent, method, request_url, request_raw))
        db.commit()
        return cursor.lastrowid  # Return the ID of the inserted request
    
    def update_log_request_response_status(self, request_id, response_status):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE requests SET response_status = ? WHERE id = ?
            """, (response_status, request_id))
        db.commit()
        return cursor.rowcount  # Return the number of rows updated

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
        self.temp_job_directory = os.path.join(tempfile.gettempdir(), 'dam-zipper')
        self.logger = logger
        self.job_id = job_id
        self.remote_base_dir = None  # Store the higher-level directory

    def download(self, file_map):
        for remote_file, local_name in file_map.items():
            try:
                # Extract the higher-level directory from the first remote file path
                if not self.remote_base_dir:
                    self.remote_base_dir = remote_file.split('/')[0]
                
                # Split the local name into directory and filename
                local_dir, filename = os.path.split(local_name)
                local_dir_path = os.path.join(self.temp_job_directory, local_dir)
                if not os.path.exists(local_dir_path):
                    os.makedirs(local_dir_path)  # Create any necessary directories

                remote_file_path = os.path.join(self.operation_profile.download_path, remote_file)
                remote_download_path = f'{self.operation_profile.name}:{remote_file_path}'

                # Set the destination file path
                destination_file_path = os.path.join(local_dir_path, secure_filename(filename))

                # Construct the rclone command
                rclone_command = [
                    'rclone', 'copyto',
                    remote_download_path,  # Remote file path (including remote name)
                    destination_file_path  # Local destination path
                ]

                # Execute the rclone command
                subprocess.run(rclone_command, check=True)

                if DEBUG:
                    self.logger.log(f"Downloaded {remote_file} to {destination_file_path}")

                self.logger.log_job(self.job_id, f"Downloaded {remote_file} to {destination_file_path}")
            except subprocess.CalledProcessError as e:
                self.logger.log_error(f"rclone failed to download {remote_file}: {e}")
                self.logger.log_job(self.job_id, f"Failed to download {remote_file}: {e}")
            except Exception as e:
                self.logger.log_error(f"Failed to download {remote_file}: {e}")
                self.logger.log_job(self.job_id, f"Failed to download {remote_file}: {e}")

    def zip(self, zip_name):
        zip_dir = self.temp_job_directory
        zip_path = os.path.join(zip_dir, secure_filename(zip_name) + '.zip')
        
        if not os.path.exists(zip_dir):
            os.makedirs(zip_dir)

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.temp_job_directory, topdown=True):
                    self.logger.log(f"Zipping: Current directory: {root}")  # Debug print
                    dirs[:] = [d for d in dirs if os.path.join(root, d) != zip_dir]
                    for file in files:
                        if file == '.DS_Store' or file == os.path.basename(zip_path):
                            continue
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start=self.temp_job_directory)
                        zipf.write(file_path, arcname)
                        self.logger.log(f"Added {file_path} to zip as {arcname}")  # Debug print

                self.logger.log(f"Zipping completed: {zip_path}")  # Debug print
                self.logger.log_job(self.job_id, f"Zipping completed: {zip_path}")

        except Exception as e:
            self.logger.log_error(f"Exception during zipping: {e}")
            self.logger.log_job(self.job_id, f"Exception during zipping: {e}")

            return None
        
        return zip_path

    def upload(self, zip_path):
        try:
            # Calculate SHA1
            local_sha1 = self.calculate_sha1(zip_path)
            self.logger.log_job(self.job_id, f"Local SHA1 checksum: {local_sha1}")
            self.logger.log(f"Local SHA1 checksum: {local_sha1}")

            # Use the remote_base_dir to define the remote upload directory

            # Construct the full remote upload path
            remote_upload_dir = f'{self.operation_profile.name}:{os.path.join(self.operation_profile.upload_path, self.remote_base_dir)}'
            remote_upload_path = f"{remote_upload_dir}/{os.path.basename(zip_path)}"

            # Construct the rclone command for uploading
            rclone_command = [
                'rclone', 'copyto',
                zip_path,  # Local source file path
                remote_upload_path  # Remote destination path
            ]

            # Execute the rclone command
            subprocess.run(rclone_command, check=True)

            self.logger.log_job(self.job_id, f"Uploaded {zip_path} to {remote_upload_path}")
            self.logger.log(f"Uploaded {zip_path} to {remote_upload_path}")  # Debug print

            # Fetch the remote file's SHA1 checksum
            remote_sha1_command = ['rclone', 'hashsum', 'SHA1', f"{remote_upload_path}"]
            result = subprocess.run(remote_sha1_command, check=True, capture_output=True, text=True)

            # Parse the SHA1 checksum from the command output
            if result.stdout:
                remote_sha1 = result.stdout.split()[0]
                self.logger.log(f"Remote SHA1 checksum: {remote_sha1}")

                # Verify SHA1 checksums
                if local_sha1 == remote_sha1:
                    self.logger.log_job(self.job_id, "SHA1 checksum verification successful.")
                    self.logger.log("SHA1 checksum verification successful.")
                else:
                    self.logger.log_job(self.job_id, "SHA1 checksum verification failed. File may be corrupted during transfer.")
                    self.logger.log_error("SHA1 checksum verification failed. File may be corrupted during transfer.")
            else:
                self.logger.log_job(self.job_id, "No SHA1 checksum received from remote for file: {remote_upload_path}")
                self.logger.log_error(f"No SHA1 checksum received from remote for file: {remote_upload_path}")

        except subprocess.CalledProcessError as e:
            self.logger.log_error(f"rclone failed to upload {zip_path}: {e}")
            self.logger.log_job(self.job_id, f"Failed to upload {zip_path}: {e}")
        except Exception as e:
            self.logger.log_error(f"Failed to upload {zip_path}: {e}")
            self.logger.log_job(self.job_id, f"Failed to upload {zip_path}: {e}")

    def cleanup(self):
        if os.path.exists(self.temp_job_directory):
            for root, _, files in os.walk(self.temp_job_directory):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        os.remove(file_path)
                        self.logger.log_job(self.job_id, f"Deleted '{file_path}'")
                        self.logger.log(f"Deleted '{file_path}'")  # Debug print
                    except Exception as e:
                        self.logger.log_error(f"Failed to delete '{file_path}': {e}")
                        self.logger.log_job(self.job_id, f"Failed to delete '{file_path}': {e}")

    def calculate_md5(self, file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def calculate_sha1(self, file_path):
        """Calculate the SHA1 hash of a file."""
        hash_sha1 = hashlib.sha1()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha1.update(chunk)
        return hash_sha1.hexdigest()

# OperationProfile class
class OperationProfile:
    # Placeholder for actual server profile logic
    def __init__(self, name, download_path, upload_path):
        self.name = name
        self.download_path = download_path
        self.upload_path = upload_path

@app.route('/submit_job', methods=['POST'])
def submit_job():
    try:
        payload = request.json
        logger = Logger()

        # Log the request and get the ID
        request_id = logger.log_request(
            source_ip=request.remote_addr, 
            user_agent=request.headers.get('User-Agent'),
            method=request.method,
            request_url=request.path,
            request_raw=json.dumps(payload)
        )

        if not request_id:
            return jsonify({'message': 'Error occurred during request submission'}), 400

        # Validate API Key
        if payload.get('auth') != os.getenv('API_KEY'):
            return jsonify({'message': 'Error, not-authorized'}), 403

        # Validate payload
        if not isinstance(payload.get('files'), dict) or not payload['files']:
            return jsonify({'message': 'Error, \'files\' array is empty or invalid'}), 400
        
        if not payload.get('server'):
            return jsonify({'message': 'Error, \'server\' string is empty'}), 400

        if not payload.get('token'):
            return jsonify({'message': 'Error, \'token\' string is empty'}), 400

        operation_profile = get_operation_profile_by_name(payload['server'])
        if not operation_profile:
            return jsonify({'message': 'Failed to match server-operation profile'}), 400

        # Create a new job record
        job_id = logger.create_job_record(request_id, json.dumps(payload))
        logger.update_log_request_response_status(request_id, 201)

        return jsonify({'message': 'Job submitted successfully', 'job_id': job_id}), 201
    
    except Exception as e:
        logger.log_error(f"Unexpected error: {str(e)}")
        return jsonify({'message': 'Unexpected error occurred'}), 500

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
                    server = payload.get('server', '')
                    token = payload.get('token', '')

                    if not files or not server or not token:
                        # missing data to continue
                        # Update job status to 'failed' and record end time
                        db.execute('''
                            UPDATE jobs SET status = 'failed', end_time = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (job_id,))
                    else:
                        # Update job status to 'in progress' and record start time
                        db.execute('''
                            UPDATE jobs SET status = 'in progress', start_time = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (job_id,))

                        try:
                            # Process the job
                            #operation_profile = OperationProfile(server)
                            operation_profile = get_operation_profile_by_name(server)

                            if operation_profile:

                                print("STARTING TO PROCESS A JOB...")
                                current_thread = threading.current_thread()
                                print(f"\tCurrent Thread Name: {current_thread.name}")
                                print(f"\tCurrent Thread ID: {current_thread.ident}")
                                print(f"\tIs Current Thread Alive: {current_thread.is_alive()}")
                                print(f"\tIs Current Thread Daemon: {current_thread.daemon}")

                                file_ops = FileOps(operation_profile, logger, job_id)

                                # Perform the download
                                file_ops.download(files)

                                # Perform the zipping
                                zip_path = file_ops.zip(token)
                                if zip_path is not None:
                                    # Only proceed if zipping was successful
                                    file_ops.upload(zip_path)

                                    # Perform cleanup after processing
                                    file_ops.cleanup()

                                    # Update job status to 'completed' and record end time
                                    db.execute('''
                                        UPDATE jobs SET status = 'completed', end_time = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    ''', (job_id,))
                                else:
                                    # Handle zipping failure
                                    logger.log_error(f"Zipping failed for job ID {job_id}")
                                    db.execute('''
                                        UPDATE jobs SET status = 'failed', end_time = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    ''', (job_id,))
                            else:
                                logger.log_error(f"Failed to match operation profile '{server}'")
                                logger.log_job(job_id, f"Failed to match operation profile '{server}'")

                                # Update job status to 'failed' and record end time
                                db.execute('''
                                UPDATE jobs SET status = 'failed', end_time = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (job_id,))

                        except Exception as e:
                            # In case of error, log and update job status
                            db.execute('''
                                UPDATE jobs SET status = 'failed', end_time = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (job_id,))

            if DEBUG:
                print("Sleeping...zzzZZZZzzzz")

            time.sleep(10)  # Check for new jobs every 10 seconds



# Global variable to hold the reference to the job_processor thread
job_processor_thread = None

def start_job_processor_thread():
    global job_processor_thread

    if job_processor_thread is None or not job_processor_thread.is_alive():
        job_processor_thread = threading.Thread(target=job_processor, daemon=True)
        job_processor_thread.start()
        print(f"Job processor thread started: {job_processor_thread.name}")

#if __name__ == '__main__':
#    init_db()  # Initialize the database
#
#    # Start the job processor thread only in the main process
#    if not DEBUG or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
#        start_job_processor_thread()
#
#    app.run(host="0.0.0.0", debug=DEBUG)

