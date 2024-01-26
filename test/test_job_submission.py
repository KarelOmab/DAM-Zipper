import unittest
from unittest.mock import patch
from flask import json
from main import app  # Import your Flask app here

class TestJobSubmission(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.endpoint = '/submit_job'
        self.sample_request = {
            "files": {
                "12345_iegurh3987wbgieubrgh9w3ug/i3hgiushgidhiudsfhg.mp4": "12345_Karel_Tutsu_VHS_07.mp4",
                "12345_iegurh3987wbgieubrgh9w3ug/gehegrheurhksjdfneu.wav": "12345_Karel_Tutsu_CC_04_SideA.wav",
                "12345_iegurh3987wbgieubrgh9w3ug/h395ghuehv893ygs084.jpg": "Album_07/image_0186.jpg"
            },
            "server": "myremote_a",
            "token": "seiurghweiourghweiur",
            "auth": "^D93T@C^?LHp]LEpQj_DGiRCmNzcQxkh"
        }

    @patch('main.Logger.log_request')
    @patch('main.Logger.create_job_record')
    def test_submit_job_positive(self, mock_create_job_record, mock_log_request):
        mock_log_request.return_value = 1  # Simulating a request ID
        mock_create_job_record.return_value = 1  # Simulating a job ID

        response = self.client.post(self.endpoint, data=json.dumps(self.sample_request), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('Job submitted successfully', response.json['message'])


    @patch('main.Logger.log_request')
    @patch('main.Logger.create_job_record')
    def test_submit_job_negative(self, mock_create_job_record, mock_log_request):
        mock_log_request.return_value = None  # Simulate a failure in logging the request
        mock_create_job_record.return_value = None  # Simulate a failure in creating the job record

        # Send a bad request
        bad_request = {}  # An empty JSON object
        response = self.client.post(self.endpoint, data=json.dumps(bad_request), content_type='application/json')
        
        # Check for the expected 400 Bad Request response
        self.assertEqual(response.status_code, 400)
        self.assertIn('Error occurred during request submission', response.json['message'])

    @patch('main.Logger.log_request')
    @patch('main.Logger.create_job_record')
    def test_submit_job_missing_files(self, mock_create_job_record, mock_log_request):
        mock_log_request.return_value = 1
        mock_create_job_record.return_value = 1

        # Create a payload without the 'files' parameter
        request_payload = {
            "server": "dist-07",
            "token": "seiurghweiourghweiur",
            "auth": "^D93T@C^?LHp]LEpQj_DGiRCmNzcQxkh"
        }

        response = self.client.post(self.endpoint, data=json.dumps(request_payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("'files' array is empty", response.json['message'])

    @patch('main.Logger.log_request')
    @patch('main.Logger.create_job_record')
    def test_submit_job_invalid_auth(self, mock_create_job_record, mock_log_request):
        mock_log_request.return_value = 1
        mock_create_job_record.return_value = 1

        # Modify the sample request to have an invalid auth key
        invalid_auth_request = self.sample_request.copy()
        invalid_auth_request["auth"] = "invalid_auth_key"

        response = self.client.post(self.endpoint, data=json.dumps(invalid_auth_request), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertIn("not-authorized", response.json['message'])

    # Test with Invalid Auth Key
    def test_invalid_auth_key(self):
        invalid_request = self.sample_request.copy()
        invalid_request["auth"] = "invalid_auth_key"

        response = self.client.post(self.endpoint, data=json.dumps(invalid_request), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertIn("not-authorized", response.json['message'])

    # Test with Missing 'files' Parameter
    def test_missing_files_parameter(self):
        incomplete_request = self.sample_request.copy()
        del incomplete_request["files"]

        response = self.client.post(self.endpoint, data=json.dumps(incomplete_request), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("'files' array is empty", response.json['message'])

    # Test with Empty 'files' Parameter
    def test_empty_files_parameter(self):
        invalid_request = self.sample_request.copy()
        invalid_request["files"] = {}

        response = self.client.post(self.endpoint, data=json.dumps(invalid_request), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("'files' array is empty", response.json['message'])

    # Test with Missing 'server' Parameter
    def test_missing_server_parameter(self):
        incomplete_request = self.sample_request.copy()
        del incomplete_request["server"]

        response = self.client.post(self.endpoint, data=json.dumps(incomplete_request), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("'server' string is empty", response.json['message'])

    # Test with Missing 'token' Parameter
    def test_missing_token_parameter(self):
        incomplete_request = self.sample_request.copy()
        del incomplete_request["token"]

        response = self.client.post(self.endpoint, data=json.dumps(incomplete_request), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("'token' string is empty", response.json['message'])

    # Test with Invalid 'files' Format
    def test_invalid_files_format(self):
        invalid_request = self.sample_request.copy()
        invalid_request["files"] = "not_a_dict"

        response = self.client.post(self.endpoint, data=json.dumps(invalid_request), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Bad request format", response.json['message'])

    # Test with Non-existent Server in 'server' Parameter
    # This test case might need an adjustment based on your application's behavior
    def test_nonexistent_server(self):
        invalid_request = self.sample_request.copy()
        invalid_request["server"] = "nonexistent_server"

        response = self.client.post(self.endpoint, data=json.dumps(invalid_request), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Failed to match server-operation profile", response.json['message'])

    # Test with Database Connection Error
    #@patch('main.get_db')
    #def test_database_connection_error(self, mock_get_db):
    #    mock_get_db.side_effect = Exception("Database connection error")
#
    #    response = self.client.post(self.endpoint, data=json.dumps(self.sample_request), content_type='application/json')
    #    self.assertEqual(response.status_code, 500)
    #    self.assertIn("Database error", response.json['message'])

    # Test with Unexpected Exception
    @patch('main.Logger.create_job_record')
    def test_unexpected_exception(self, mock_create_job_record):
        # Simulate an unexpected exception
        mock_create_job_record.side_effect = Exception("Unexpected error")

        response = self.client.post(self.endpoint, data=json.dumps(self.sample_request), content_type='application/json')
        self.assertEqual(response.status_code, 500)


    
