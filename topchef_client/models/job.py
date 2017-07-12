"""
Describes a TopChef Job
"""
import requests
from ..exceptions import NetworkError


class Job(object):
    """
    Base class for a job
    """
    _JSON_header = {'Content-Type': 'application/json'}

    HTTP_STATUS_CODE_OK = 200

    def __init__(self, topchef_url, job_id, http_library=requests):
        """

        :param str topchef_url: The base URL to the TopChef API
        :param UUID job_id: The Job ID
        :param mod http_library: The library to use for making HTTP requests
        """
        self._http_library = http_library
        self._topchef_url = topchef_url
        self.job_id = job_id

    @property
    def is_complete(self):
        return self.status == u'COMPLETED'

    @property
    def job_details_endpoint(self):
        """

        :return: The URL to the job details
        :rtype: str
        """
        return '{0}/jobs/{1}'.format(self._topchef_url, str(self.job_id))

    @property
    def result(self):
        """
        :return: The result for the job
        :rtype: object
        """
        return self.job_details['result']

    @result.setter
    def result(self, new_result):
        """

        :param object new_result: The new result to set
        :return: The result
        """
        job_details = self.job_details
        job_details['result'] = new_result
        self.job_details = job_details

    @property
    def status(self):
        return self.job_details['status']

    @property
    def job_details(self):
        """

        :return: The details for the job
        """
        response = self._http_library.get(
            self.job_details_endpoint, headers=self._JSON_header
        )

        if response.status_code != self.HTTP_STATUS_CODE_OK:
            self._handle_http_error(response.status_code)

        return response.json()['data']

    @job_details.setter
    def job_details(self, new_job_details):
        """
        Fire off a PUT request to set the new job details

        :param new_job_details: The new job details
        """
        response = self._http_library.put(
            self.job_details_endpoint, headers=self._JSON_header,
            json=new_job_details
        )

        if response.status_code != self.HTTP_STATUS_CODE_OK:
            self._handle_set_job_details_error(response.status_code)

    @staticmethod
    def _handle_http_error(status_code):
        raise NetworkError(
            """Attempting to get job details resulted in unexpected status \ 
            code {0}""".format(status_code)
        )

    @staticmethod
    def _handle_set_job_details_error(status_code):
        raise NetworkError(
            """Attempting to set job details returned unexpected status 
            code {0}""".format(status_code)
        )
