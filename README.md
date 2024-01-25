
# DAM-Zipper

DAM Zipper API is a RESTful API developed using Python and Flask, designed to manage file operations such as downloading, zipping, and uploading files using remote servers. It utilizes SQLite for data storage and provides structured logging and job management capabilities.

## Features

- **File Operations**: Supports downloading, zipping, and uploading files.
- **RESTful API**: Easy integration with other services.
- **SQLite Database**: Uses SQLite for storing requests, jobs, and events data.
- **Asynchronous Job Processing**: Handles jobs asynchronously, allowing the API to remain responsive.
- **Structured Logging**: Logs all activities, errors, and job statuses.

## Requirements

- Python 3.x
- Flask
- SQLite3
- Rclone (for remote file operations)
- Additional Python libraries: `werkzeug`, `subprocess`, `threading`, `json`, `tempfile`, `dotenv`

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/[your-repository]/dam-zipper-api.git
   cd dam-zipper-api
   ```

2. Install dependencies
```pip install -r requirements.txt```

3. Set up your `.env` file with API-key
```API_KEY=^D93T@C^?LHp]LEpQj_DGiRCmNzcQxkh```

3. Set up your `rclone-profiles` files in the **/profiles** directory
	```
	NAME=myremote_a
	PATH_DOWN=/Users/Karel/Desktop/REMOTE_A
	PATH_UP=/Users/Karel/Desktop/REMOTE_B
	```

## Usage
Start the Flask server:
```
python main.py
```

The server will start processing jobs asynchronously. Use the `/submit_job` endpoint to submit new jobs.

### API Endpoints

#### POST /submit_job

Submits a new job for processing.

**Request Payload**:

```
{
  "files": {
    "remote_file_path": "local_file_path",
    ...
  },
  "server": "remote_server_name",
  "token": "zip_token",
  "auth": "api_key"
}
```

**Response**:

-   201: Job submitted successfully.
-   400: Bad request, missing or invalid data.
-   403: Unauthorized access.

## Database Schema

The application uses SQLite and has the following schema:

-   `requests`: Stores details about each API request.
-   `jobs`: Stores information about each job submitted.
-   `events`: Logs events related to job processing.
