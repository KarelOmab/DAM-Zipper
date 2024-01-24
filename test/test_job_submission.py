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
            "server": "dist-07",
            "token": "seiurghweiourghweiur"
        }

    @patch('main.Logger.log_request')
    @patch('main.Logger.create_job_record')
    def test_submit_job_positive(self, mock_create_job_record, mock_log_request):
        # Set the return value for the mocked methods
        mock_log_request.return_value = 1  # Simulating a request ID
        mock_create_job_record.return_value = 1  # Simulating a job ID

        response = self.client.post(self.endpoint, data=json.dumps(self.sample_request), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('Job submitted successfully', response.json['message'])


    @patch('main.Logger.log_request')
    @patch('main.Logger.create_job_record')
    def test_submit_job_negative(self, mock_create_job_record, mock_log_request):
        # Set up the mock to simulate a failure in logging the request or creating the job record
        mock_log_request.return_value = None  # Simulate a failure in logging the request
        mock_create_job_record.return_value = None  # Simulate a failure in creating the job record

        # Send a bad request
        bad_request = {}  # An empty JSON object
        response = self.client.post(self.endpoint, data=json.dumps(bad_request), content_type='application/json')
        
        # Check for the expected 400 Bad Request response
        self.assertEqual(response.status_code, 400)
        self.assertIn('Error occurred during job submission', response.json['message'])
