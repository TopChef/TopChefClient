"""
Contains unit tests for :mod:`topchef_client.api_model.job`
"""
import unittest
import requests
from topchef_client.api_model.job import Job
from uuid import uuid4
from mock import MagicMock, call


class TestJob(unittest.TestCase):
    """
    Base class for unit tests of :mod:`topchef_client.api_model.job`
    """
    def setUp(self):
        self.http_library = MagicMock(spec=requests)
        self.topchef_url = 'http://mock.url/topchef'
        self.job_id = uuid4()
        self.job = Job(self.topchef_url, self.job_id, self.http_library)

    def tearDown(self):
        self.http_library.reset_mock()

    class MockResponse(object):
        def __init__(self, status_code, return_json):
            self.status_code = status_code
            self._data = return_json

        def json(self):
            return self._data


class TestResult(TestJob):
    """
    Contains unit tests for :meth:`topchef_client.api_model.job.Job.result
    """
    JSON_headers = {'Content-Type': 'application/json'}

    def setUp(self):
        TestJob.setUp(self)
        self.result = 'result'
        self.mock_response = {
            'data': {
                'result': self.result
            }
        }
        self.http_library.get = MagicMock(
            return_value=self.MockResponse(200, self.mock_response)
        )

        self.http_library.put = MagicMock(
            return_value=self.MockResponse(200, {})
        )

    def test_result_getter(self):
        expected_http_get_call = call(
            self.job.job_details_endpoint,
            headers=self.JSON_headers
        )

        self.assertEqual(self.result, self.job.result)
        self.assertEqual(
            expected_http_get_call, self.http_library.get.call_args
        )

    def test_result_setter(self):
        new_result = 'foo'
        self.job.result = new_result

        expected_put_call = call(
            self.job.job_details_endpoint,
            headers=self.JSON_headers,
            json={'result': new_result}
        )

        self.assertEqual(
            expected_put_call, self.http_library.put.call_args
        )
