"""
Contains unit tests for :mod:`topchef_client.api_model.service`
"""
import requests
from unittest import TestCase
from mock import MagicMock, call
from uuid import uuid4
from topchef_client.api_model.service import Service


class TestService(TestCase):
    """
    Base class for unit testing services
    """
    def setUp(self):
        self.topchef_url = 'http://fakeurl.fake/topchef'
        self.job_id = uuid4()
        self.http_library = MagicMock(spec=requests)

        self.service = Service(
            self.topchef_url, self.job_id, self.http_library
        )

    def tearDown(self):
        self.http_library.reset_mock()

    class MockResponse(object):
        def __init__(self, status_code, data):
            self.status_code = status_code
            self._data = data

        def json(self):
            return self._data


class TestJobRegistrationSchema(TestService):
    def setUp(self):
        TestService.setUp(self)
        self.job_registration_schema = {'type': 'object'}
        self.job_registration_instance = {'waitTime': 10}

    def test_getter(self):
        response = self.MockResponse(
            200,
            {
                'data': {
                    'job_registration_schema': self.job_registration_schema
                }
            }
        )
        self.http_library.get = MagicMock(return_value=response)

        self.assertEqual(
            self.job_registration_schema, self.service.job_registration_schema
        )


class TestNewJob(TestService):

    JSON_header = {'Content-Type': 'application/json'}

    def setUp(self):
        TestService.setUp(self)
        self.validator_factory = MagicMock()
        self.parameters = {'WaitTime': 10}

        self.expected_new_job_id = uuid4()

    def tearDown(self):
        self.validator_factory.reset_mock()
        TestService.tearDown(self)

    @property
    def mock_json_data_for_post(self):
        return {'parameters': self.parameters}

    @property
    def mock_response(self):
        return {'data': {'job_details': {'id': self.expected_new_job_id}}}

    def test_new_job(self):
        self.http_library.post = MagicMock(
            return_value=self.MockResponse(201, self.mock_response)
        )
        self.http_library.get = MagicMock(
            return_value=self.MockResponse(200, MagicMock())
        )

        self.validator_factory().assert_instance_matches_schema = MagicMock()

        job = self.service.new_job(self.parameters, self.validator_factory)
        self.assertEqual(self.expected_new_job_id, job.job_id)
        self.assertEqual(self.http_library, job._http_library)

        expected_post_call = call(
            self.service.new_job_endpoint, headers=self.JSON_header,
            json=self.mock_json_data_for_post
        )

        self.assertEqual(
            expected_post_call,
            self.http_library.post.call_args
        )
