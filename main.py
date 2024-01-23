from flask import Flask, request, jsonify, g
import sqlite3
import os
import zipfile
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)

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
    def log(self, message):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO logs (message) VALUES (?)", (message,))
        db.commit()

# Job class
class Job:
    def __init__(self, request_data, file_ops, operation_profile):
        self.request_data = request_data
        self.file_ops = file_ops
        self.operation_profile = operation_profile

class FileOps:
    def __init__(self, operation_profile):
        self.operation_profile = operation_profile
        self.temp_job_directory = os.path.join(os.getcwd(), 'temp')

    def download(self, file_map):
        # Simulate downloading files by copying from the source to the temporary job directory
        for remote_file, local_name in file_map.items():
            directory_path, file_name = os.path.split(remote_file)
            source_file_path = os.path.join(self.operation_profile.download_path, directory_path, file_name)
            destination_file_path = os.path.join(self.temp_job_directory, secure_filename(local_name))
            shutil.copy2(source_file_path, destination_file_path)  # This will copy the file and preserve its metadata
            print(f"Simulated download of {remote_file} to {destination_file_path}")

    def zip(self, files, zip_name):
        # Placeholder for zip logic
        # Create a ZIP file with the specified zip_name containing all the files
        zip_path = os.path.join(self.operation_profile.zip_path, secure_filename(zip_name) + '.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file in files.values():
                file_path = os.path.join(self.temp_job_directory, secure_filename(file))
                zipf.write(file_path, arcname=file)
        return zip_path

    def upload(self, zip_path):
        # Placeholder for upload logic
        # 'Upload' the ZIP file to the operation_profile's upload_path
        # This is a dummy function to simulate upload
        print(f"Simulated upload of {zip_path} to {self.operation_profile.upload_path}")

# OperationProfile class
class OperationProfile:
    # Placeholder for actual server profile logic
    def __init__(self, profile_name):
        self.profile_name = profile_name
        self.download_path = os.path.join(os.getcwd(), 'sample_files')
        self.zip_path = os.path.join(os.getcwd(), 'temp')
        self.upload_path = '/dummy/path/for/upload/'  # Example upload path

# HTTP request handler
@app.route('/job', methods=['POST'])
def create_job():
    payload = request.json
    files = payload.get('files', {})
    server = payload.get('server', 'default_profile')
    token = payload.get('token', 'default_zip_name')

    operation_profile = OperationProfile(server)
    file_ops = FileOps(operation_profile)
    
    logger = Logger()
    logger.log(f"Received job request with data: {payload}")

    # Process files
    file_ops.download(files)
    zip_path = file_ops.zip(files, token)
    file_ops.upload(zip_path)

    # Create Job object (not shown in the payload processing, but you would typically do this)
    job = Job(request.json, file_ops, operation_profile)
    # Enqueue job and other necessary actions

    return jsonify({"message": "Job created and processed", "zip_path": zip_path}), 201

if __name__ == '__main__':
    init_db()  # Make sure to initialize the database
    app.run(debug=True)
