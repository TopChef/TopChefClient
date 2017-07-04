"""
Describes a TopChef service
"""
import requests
from topchef_client.exceptions import NetworkError
from topchef_client.api_model.validator import Validator
from .job import Job


class Service(object):
    """
    Represents a TopChef service
    """
    _JSON_header = {'Content-Type': 'application/json'}

    HTTP_STATUS_CODE_OK = 200
    HTTP_STATUS_CODE_CREATED = 201

    def __init__(self, service_id, topchef_url, http_library=requests):
        """

        :param service_id: The ID for the service
        :param topchef_url: The base URL for the TopChef API
        :param http_library: The library to use for HTTP requests
        """
        self.service_id = service_id
        self.topchef_url = topchef_url
        self._http_library = http_library

    @property
    def _service_endpoint(self):
        """

        :return: A URL for getting details for a particular service
        :rtype: str
        """
        return '{0}/services/{1}'.format(self.topchef_url, self.service_id)

    @property
    def does_service_exist(self):
        """

        :return: A boolean that is true if the service exists. A sufficient
        condition for existence of the service is if the GET request to the
        service endpoint returns the OK status code
        """
        response = self._http_library.get(
            self._service_endpoint, headers=self._JSON_header
        )
        return response.status_code == self.HTTP_STATUS_CODE_OK

    @property
    def new_job_endpoint(self):
        return '{0}/services/{1}/jobs'.format(
            self.topchef_url, self.service_id
        )

    @property
    def job_registration_schema(self):
        """

        :return: The schema that must be satisfied in order to post jobs to
            this service
        :rtype: dict
        """
        data = self._get_data()
        return data['job_registration_schema']

    def new_job(self, parameters, validator_factory=Validator):
        """

        :param dict parameters: The parameters to use for the job
        :param type validator_factory: The JSON Schema validator to use for
            checking the parameters
        :return: The newly-created job
        :rtype: Job
        """
        validator = validator_factory(self.topchef_url, self._http_library)
        validator.assert_instance_matches_schema(
            parameters, self.job_registration_schema
        )

        new_job_response = self._http_library.post(
            self.new_job_endpoint, headers=self._JSON_header,
            json={'parameters': parameters}
        )

        if new_job_response.status_code != self.HTTP_STATUS_CODE_CREATED:
            self._handle_job_not_created_error(new_job_response.status_code)

        new_job_id = new_job_response.json()['data']['job_details']['id']

        return Job(self.topchef_url, new_job_id, self._http_library)

    def _get_data(self):
        """

        :return: A dictionary representing the details for a service
        """

        job_data_response = self._http_library.get(
            self._service_endpoint, headers=self._JSON_header
        )

        if job_data_response.status_code != self.HTTP_STATUS_CODE_OK:
            self._handle_http_error(job_data_response.status_code)
        else:
            return job_data_response.json()['data']

    @staticmethod
    def _handle_http_error(response_code):
        """

        :param response_code: The offending status code
        :raises: NetworkError
        """
        raise NetworkError(
            'Unable to contact server. Request for data '
            'returned status code %s' % response_code
        )

    @staticmethod
    def _handle_job_not_created_error(status_code):
        """

        :param status_code: The offending status code
        :raises: NetworkError
        """
        raise NetworkError(
            'Attempting to create job returned unexpected status code %s' %
            status_code
        )
