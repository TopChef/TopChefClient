"""
Contains a base class for a client capable of working with the TopChef
client
"""
import threading
import requests
import abc
import six
import json
import time

class NetworkError(IOError, RuntimeError):
    pass

class ValidationError(ValueError):
    def __init__(self, message, context, *args, **kwargs):
        ValueError.__init__(self, *args, **kwargs)
        self.message = message
        self.context = context

    def __str__(self):
        return 'ValueError: message=%s, context=%s' % (
            self.message, self.context)

class ProcessingError(RuntimeError):
    pass

@six.add_metaclass(abc.ABCMeta)
class Client(object):

    def __init__(self, address, service_id, timeout=30):
        """
        Initialize a client to listen on a server
        and look for jobs for the next service id
        
        :param str address: The hostname of the topchef API on which
            the client is to listen
        :param str service_id: The ID of the service that this client
            represents
        :param int timeout: The number of seconds that the polling
            thread should wait before sending a PATCH request to the
            server. The client contains a thread for polling the API
            periodically, so that the API knows that a particular service
            has an instance of a client bound to it, ready to accept jobs.
        """
        self.address = address
        self.id = service_id
        self.timeout = timeout
        
        self.polling_thread = threading.Thread(target=self._polling_loop)
        self.polling_thread.daemon = True # In these Daemon Days ...

        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True

    @abc.abstractmethod
    def run(self, parameters):
        raise NotImplementedError
    
    @classmethod
    def new_service(cls, 
        address, name, description, job_registration_schema,
        job_result_schema={'type':'object'}
    ):
        """
        Create a new service and bind the client to accept jobs
        using this service

        :param str address: The hostname of the topchef API on which
            the client is to listen
        :param str description: The description that will accompany
            the newly-created service
        :param str description: The service description
        :param dict job_registration_schema: The JSON schema that must
            be satisfied in order to submit a job
        :param dict job_result_schema: The schema that must be satisfied
            in order to produce a valid job result. By default, this schema
            is ``{"type": "object"}``, meaning it matches all possible
            objects.
        """
        data_to_post = {'description': description, 'name': name,
            'job_registration_schema': job_registration_schema,
            'job_result_schema': job_result_schema}


        endpoint = '%s/services' % address

        response = requests.post(endpoint,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(data_to_post))

        if response.status_code != 201:
            raise NetworkError(
                'Unable to create service at address %s. Status code %s' % (
                endpoint, response.status_code
            ))
        else:
            service_id = response.json()['data']['service_details']['id']
            return cls(address, service_id)

    @property
    def is_server_alive(self):
        response = requests.get(
            self.address, headers={'Content-Type': 'application/json'}
        )
        return response.status_code == 200

    @staticmethod
    def _json_get(endpoint):
        response = requests.get(endpoint,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            raise NetworkError(
                'Unable to connect to %s. status code %s' % 
                    (endpoint, response.status_code)
            )

        return response.json()

    @property
    def _service_details(self):
        endpoint = '%s/services/%s' % (self.address, self.id)
        response = self._json_get(endpoint)
        return response['data']
        
    @property
    def job_registration_schema(self):
        return self._service_details['job_registration_schema']

    @property
    def job_result_schema(self):
        return self._service_details['job_result_schema']

    @property
    def _first_job_id_in_queue(self):
        queue_endpoint = '%s/services/%s/queue' % (self.address, self.id)

        job_id = self._json_get(queue_endpoint)['data'][0]['id']

        return job_id

    @property
    def current_job(self):
        job_id = self._first_job_id_in_queue
        
        endpoint = '%s/jobs/%s' % (self.address, job_id)

        details = self._json_get(endpoint)['data']

        return _Job(self.address, details)

    @property
    def is_queue_empty(self):
        queue_endpoint = '%s/services/%s/queue' % (self.address, self.id)

        data = self._json_get(queue_endpoint)['data']

        return data == []

    @classmethod
    def check_in_to_server(cls, address, service_id):
        """
        Send a PATCH request to the server to let the server know
        that this class still exists and is accepting jobs
        """
        endpoint = '%s/services/%s' % (address, service_id)

        response = requests.patch(endpoint)

        if response.status_code != 200:
            raise NetworkError(
                'Unable to check in service %s at address %s' % (
                    service_id, address)
            )

    def _polling_loop(self):
        """
        Starts an unescaped loop to poll the server.

        .. note::
            Should only be run in the polling thread. This will block
            your program if it's run in the main thread.
        """
        while self.is_server_alive:
            self.check_in_to_server(self.address, self.id)
            time.sleep(self.timeout)

    def _processing_loop(self):
        """
        Responsible for fetching the job parameters, running the run method,
        and validating the runner results against the result schema
        """
        while self.is_server_alive:
            if self.is_queue_empty: continue
            else: self.run_iteration()

    def run_iteration(self):
        parameters = self.current_job['parameters']
        
        try:
            self.validate_schema(parameters, self.job_registration_schema)
        except ValidationError:
            raise ProcessingError(
                'Unable to validate instance %s against schema %s' % (
                    parameters, self.job_registration_schema
                )
            )

        self.current_job.status = "WORKING"

        results = self.run(parameters)

        try:
            self.validate_schema(results, self.job_result_schema)
        except ValidationError:
            raise ProcessingError(
                'Unable to validate result %s against schema %s' % (
                    result, self.job_result_schema
                )
            )

        self.current_job.result = results
        self.current_job.status = "COMPLETED"

    def start(self, should_poll=True):
        """
        Start the client's main processing loop. Start a polling loop in a separate thread
        """
        if should_poll: self.polling_thread.start()
        self.processing_thread.start()

    def validate_schema(self, instance, schema):
        """
        POST to the API to check if a dictionary instance
        is a valid instance of the provided schema
        """
        endpoint = '%s/validator' % self.address

        data_to_post = {'object': instance, 'schema': schema}

        response = requests.post(endpoint,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(data_to_post)
        )

        if response.status_code == 400:
            data = response.json()['errors']
            raise self.ValidationError(data['message'], data['context'])
        elif response.status_code != 200:
            raise NetworkError('Unable to connect to %s')


class _Job(object):
    def __init__(self, address, job_dict):
        self.address = address
        self._job_dict = job_dict

    def __getitem__(self, item):
        return self._job_dict[item]

    @property
    def id(self):
        return self._job_dict['id']

    @property
    def status(self):
        return self._job_dict['status']

    @status.setter
    def status(self, new_status):
        if new_status not in ["REGISTERED", "WORKING", "COMPLETED"]:
            raise ValueError(
                "The status must be one of 'REGISTERED', 'WORKING', or "\
                "'COMPLETED'"
            )

        self._job_dict['status'] = new_status

        self._update()
   
    @property
    def result(self):
        return self._job_dict['result']

    @result.setter
    def result(self, result):
        self._job_dict['result'] = result

        self._update()

    def _update(self):
        endpoint = '%s/jobs/%s' % (self.address, self.id)

        response = requests.put(endpoint,
            headers={'Content-Type': 'application/json'},
            data = json.dumps(self._job_dict)
        )

        if response.status_code != 200:
            raise NetworkError(
                'Unable to PUT new job dict %s on endpoint %s' % (
                    self._job_dict, endpoint)
            )

