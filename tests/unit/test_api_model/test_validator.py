"""
Contains unit tests for :mod:`topchef_client.api_model.validator`
"""
import unittest
import requests
from mock import MagicMock
from uuid import uuid4
from topchef_client.exceptions import ProcessingError
from topchef_client.api_model.validator import Validator


class TestValidator(unittest.TestCase):
    """
    Base class for validator unit tests
    """
    def setUp(self):
        self.service_id = uuid4()
        self.topchef_url = 'http://some-address.com/topchef' 
        self.http_library = MagicMock(spec=requests)

        self.validator = Validator(self.topchef_url, self.http_library)

    def tearDown(self):
        self.http_library.reset_mock()

    class MockResponse(object):
        """
        Wraps HTTP responses in order to allow stubbing of the HTTP
        library in a reasonable way
        """
        def __init__(self, status_code, data=None):
            if data is None:
                data = {}

            self.status_code = status_code
            self._data = data

        def json(self):
            """

            :return: The json that was supplied in the response constructor
            :rtype dict:
            """
            return self._data


class TestDoesInstanceMatchSchema(TestValidator):
    """
    Contains unit tests for the validation method
    """
    HTTP_STATUS_CODE_OK = 200
    HTTP_STATUS_CODE_BAD_REQUEST = 400

    def setUp(self):
        TestValidator.setUp(self)
        self.instance = {'data': 'testing'}
        self.schema = {'type': 'object'}

    def test_validator_good_response(self):
        validation_strategy = self.AlwaysTrueValidator()

        self.validator.assert_instance_matches_schema(
            self.instance, self.schema, validator=validation_strategy
        )

    def test_validator_bad_response(self):
        validation_strategy = self.AlwaysFalseValidator()

        with self.assertRaises(ProcessingError):
            self.validator.assert_instance_matches_schema(
                self.instance, self.schema, validator=validation_strategy
            )

    class AlwaysTrueValidator(Validator.AbstractValidator):
        """
        Describes a JSON schema validator that is always true
        """
        def does_instance_match_schema(self, instance, schema):
            return True

    class AlwaysFalseValidator(Validator.AbstractValidator):
        def does_instance_match_schema(self, instance, schema):
            return False

