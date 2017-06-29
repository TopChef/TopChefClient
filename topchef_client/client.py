"""
Contains a class that provides a method for working 

In the context of the API, a service is a resource capable of polling the
API, taking in a single JSON object corresponding to a schema, and returning
a result which is a valid instance of a result schema. A job is a
resource which contains a parameter dictionary satisfying the service schema.

In order to use this client, :class:`Client` needs to be subclassed, and its
:meth:`run` method needs to be implemented. The argument of :meth:`run`
is guaranteed to satisfy the service's job registration schema. However, the
onus is on the user to ensure that the return value satisfies the job result
schema of the job's service.

In accordance with the Python convention, properties and methods beginning 
with ``_`` are private.
"""
import threading
import requests
import abc
import six
import json
import time


class NetworkError(IOError, RuntimeError):
    """
    Thrown if the client is unable to connect to the server,
    or recieves an unexpected response from the server.
    """
    pass


class ValidationError(ValueError):
    """
    Thrown if a JSON object does not conform to a required
    JSON schema. This exception takes in the message and context
    from the API.

    :var str message: The message that the API returns from
        validating the schema
    :var [str] context: The context in which the error occurred
    """
    def __init__(self, message, context, *args, **kwargs):
        """
        Instantiates the variables described above
        """
        ValueError.__init__(self, *args, **kwargs)
        self.message = message
        self.context = context

    def __str__(self):
        """
        Returns a string representation of the exception
        """
        return 'ValueError: message=%s, context=%s' % (
            self.message, self.context)


class ProcessingError(RuntimeError):
    """
    Thrown if an error occurs while executing :meth:`run` in a processing
    thread
    """
    pass


@six.add_metaclass(abc.ABCMeta)
class Client(object):
    """
    Abstract base class that consumes the TopChef API, passes the parameters
    to :meth:`run`, and returns the result to the server. The work is done
    in a background thread. 

    The main thread of the application checks if there are any jobs available
    in a service's queue. If there are jobs available, it executes :meth:`run`
    with the job's parameters.
    """
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
        self.polling_thread.daemon = True  # In these Daemon Days ...

        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True

    @abc.abstractmethod
    def run(self, parameters):
        """
        Abstract method that should take in a dictionary of parameters and
        return a valid dictionary.

        :raises: :exc:`NotImplementedError` if the method is not subclassed
        """
        raise NotImplementedError
    
    @classmethod
    def new_service(cls, 
        address, name, description, job_registration_schema,
        job_result_schema={'type': 'object'}
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
        data_to_post = {
            'description': description,
            'name': name,
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
        """
        Getter that returns True if the target server is up and running
        
        :return: ``True`` if a ``GET`` request to the API is successful
            and ``False`` if not
        :rtype: bool
        """
        response = requests.get(
            self.address, headers={'Content-Type': 'application/json'}
        )
        return response.status_code == 200

    @staticmethod
    def _json_get(endpoint):
        """
        Obtain data from an endpoint and return the body of the request
        as a dictionary. This dictionary is built from the request body's
        JSON.

        :param str endpoint: The URL from which data needs to be obtained
        :return: The JSON from the endpoint
        :rtype: dict
        :raises: :exc:`NetworkError` if the response status code from
            the request is not ``200``.
        """
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
        """
        Returns the dictionary containing the details for the current
        service to which this client is bound.

        :return: The details for a service
        :rtype: dict
        """
        endpoint = '%s/services/%s' % (self.address, self.id)
        response = self._json_get(endpoint)
        return response['data']
        
    @property
    def job_registration_schema(self):
        """
        Returns the job registration schema

        :return: The schema that must be satisfied for a job to be
            registered
        :rtype: dict
        """
        return self._service_details['job_registration_schema']

    @property
    def job_result_schema(self):
        """
        Returns the schema that must be satisfied for a result to be
        posted

        :return: The job result schema
        :rtype: dict
        """
        return self._service_details['job_result_schema']

    @property
    def _first_job_id_in_queue(self):
        """
        Returns the first ID of a job in the queue

        :return: The ID of the first job in the queue
        :rtype: str
        """
        queue_endpoint = '%s/services/%s/queue' % (self.address, self.id)

        job_id = self._json_get(queue_endpoint)['data'][0]['id']

        return job_id

    @property
    def current_job(self):
        """
        Returns the current job that is to be worked on

        :return: A job that must be processed
        :rtype: _Job
        """
        job_id = self._first_job_id_in_queue
        
        endpoint = '%s/jobs/%s' % (self.address, job_id)

        details = self._json_get(endpoint)['data']

        return _Job(self.address, details)

    @property
    def is_queue_empty(self):
        """
        Returns ``True`` if the service's queue is empty and ``False`` if not.
        """
        queue_endpoint = '%s/services/%s/queue' % (self.address, self.id)

        data = self._json_get(queue_endpoint)['data']

        return data == []

    @classmethod
    def check_in_to_server(cls, address, service_id):
        """
        Send a PATCH request to the server to let the server know
        that this class still exists and is accepting jobs

        :param str address: The address that must be patched
        :param str service_id: The ID of the service that must be
            ``PATCH``ed
        :raises: :exc:`NetworkError` if the site cannot be ``PATCH``ed
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
        """
        Run a single iteration of the processing loop. This is exposed to
        enable packaging of the Client's main loop in a more elaborate
        multitasking system.
        """
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
        Start the client's main processing loop. Start a polling loop 
        in a separate thread
        
        :param bool should_poll: If true, then the polling thread will be
            started along with the processing thread
        """
        if should_poll: self.polling_thread.start()
        self.processing_thread.start()

    def validate_schema(self, instance, schema):
        """
        POST to the API to check if a dictionary instance
        is a valid instance of the provided schema

        :param dict instance: The object that must be validated
        :param dict schema: The schema against which the instance
            is to be validated
        :raises: :exc:`ValidationError` if ``instance`` does not
            validate against ``schema``
        :raises: :exc:`NetworkError` if a connection cannot be made
            to the validator endpoint
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
    """
    A private representation of a TopChef job. This class is used
    as an adapter to make business logic clearer in client definitions.

    :var str address: The base address of the TopChef server.
    :var dict job_dict: A dictionary representing the details of the job
    """
    def __init__(self, address, job_dict):
        """
        Instantiates the variables listed in the class description
        """
        self.address = address
        self._job_dict = job_dict

    def __getitem__(self, item):
        """
        Returns the corresponding entry from this job's :var:`job_dict`

        :param str item: The key from the job dict that must be obtained
        :return: the entry from the dictionary
        """
        return self._job_dict[item]

    @property
    def id(self):
        """
        Returns the job id

        :returns: the Job ID
        :rtype: str
        """
        return self._job_dict['id']

    @property
    def status(self):
        """
        Returns the job status
        
        :return: The job status
        :rtype: str
        """
        return self._job_dict['status']

    @status.setter
    def status(self, new_status):
        """
        Set a new status. Ensures that it is a valid job status prior
        to updating

        :param str new_status: The new status to set
        :raises: :exc:`ValueError` if the status is invalid
        """
        if new_status not in ["REGISTERED", "WORKING", "COMPLETED"]:
            raise ValueError(
                "The status must be one of 'REGISTERED', 'WORKING', or "\
                "'COMPLETED'"
            )

        self._job_dict['status'] = new_status

        self._update()
   
    @property
    def result(self):
        """
        Returns the job result
        """
        return self._job_dict['result']

    @result.setter
    def result(self, result):
        """
        Sets the new job result and updates the job. No
        validation is done here as it is assumed that the service
        using this :class:`_Job` has already perfored the 
        required validation

        :param dict result: The new result to set
        """
        self._job_dict['result'] = result
        self._update()

    def _update(self):
        """
        Send a ``PUT`` request to the server with the updated
        job data

        :raises: :exc:`NetworkError` if the update was not successful
        """
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

