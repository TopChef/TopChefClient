"""
Describes a JSON schema validator
"""
from ..exceptions import NetworkError, ProcessingError
import requests
from abc import ABCMeta, abstractmethod
from six import add_metaclass


class Validator(object):
    """
    Validates schemas
    """
    _JSON_header = {'Content-Type': 'application/json'}

    HTTP_STATUS_CODE_OK = 200
    HTTP_STATUS_CODE_BAD_REQUEST = 400

    def __init__(self, topchef_url, http_library=requests):
        """

        :param topchef_url: The URL for the TopChef API
        :param http_library: The library to use for HTTP calls
        """
        self._topchef_url = topchef_url
        self._http_library = http_library
        
    def assert_instance_matches_schema(self, instance, schema, validator=None):
        """

        :param dict instance: The instance to validate
        :param dict schema: The schema against which the instance is to be
            validated
        :param AbstractValidator validator: The validator to use. If this is
            None, a RemoteSchemaValidator will be constructed
        :return: True if the instance matches the schema
        :raises: NetworkError if an unexpected status code is received
        """
        if validator is None:
            validator = self.RemoteSchemaValidator(
                    self._topchef_url, self._http_library
            )

        result = validator.does_instance_match_schema(instance, schema)

        if not result:
            raise ProcessingError("The instance does not match the schema")

    @add_metaclass(ABCMeta)
    class AbstractValidator(object):
        """
        Describes the interface for an object capable of validating JSON 
        schemas. This object does the heavy lifting for validating JSON.
        It also helps with testing as the validation procedure can be stubbed
        out more efficiently.
        """

        @abstractmethod
        def does_instance_match_schema(self, instance, schema):
            """
            
            :param dict instance: The instance to validate
            :param dict schema: The schema against which the instance is to be
                validated
            """
            raise NotImplementedError()

    class RemoteSchemaValidator(AbstractValidator):
        """
        Perfoms validation remotely using the TopChef API
        """
        _JSON_header = {'Content-Type': 'application/json'}
        HTTP_STATUS_CODE_OK = 200
        HTTP_STATUS_CODE_BAD_REQUEST = 400

        def __init__(self, topchef_url, http_library=requests):
            """
            
            :param str topchef_url: The URL for the TopChef API
            :param mod http_library: The library to use for HTTP requests
            """
            self.topchef_url = topchef_url
            self._http_library = http_library

        @property
        def _validator_endpoint(self):
            """

            :return: The URL for the JSON schema validator
            """
            return '{0}/validator'.format(self.topchef_url)

        def does_instance_match_schema(self, instance, schema):
            """

            :param dict instance: The instance to validate
            :param dict schema: The schema against which the instance is to be
                validated
            :return: True if the instance matches the schema
            :raises: NetworkError if an unexpected status code is received
            """
            request_body = self._get_request_body(instance, schema)
            response = self._http_library.post(
                self._validator_endpoint, headers=self._JSON_header,
                json=request_body
            )

            return self._analyze_validation_response(response)

        def _analyze_validation_response(self, response):
            """
            Analyze whether the validation request was successful or not based
            on the status code of the response

            :param requests.Response response: The response to analyze
            :return: True if the status code is correct, and False if otherwise
            :raises: NetworkError if an unexpected status code is received
            """
            status_code = response.status_code

            if status_code == self.HTTP_STATUS_CODE_OK:
                return True
            elif status_code == self.HTTP_STATUS_CODE_BAD_REQUEST:
                return False
            else:
                raise NetworkError(
                    'Unable to contact validator. Status code %s',
                    status_code
                )

        @staticmethod
        def _get_request_body(instance, schema):
            """
            Format a request for the body of the POST request for the TopChef 
            JSON Schema validator

            :param dict instance: The instance to validate
            :param dict schema: The schema against which the instance is to
                be validated
            """
            return {'object': instance, 'schema': schema}
