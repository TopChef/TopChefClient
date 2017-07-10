Quickstart
==========

This section describes how to use the TopChef API to run experiments
remotely and programmatically.

The Quickest Quickstart Possible: Running a Ramsey Experiment Remotely
----------------------------------------------------------------------

Consider a Ramsey experiment to be repeated 50000 times, using a pulse time
of 10 nanoseconds, a time between pulses of 1 microsecond, and no pulse phase.
A script to run an experiment like this is given below. Assume there is a
running TopChef server on ``localhost:5000``, and the NV experiments are
exposed using the UUID ``1e566b07-8011-46f1-b39b-8a8c5700c352``.

.. code-block:: python

    """
    Running an experiment from start to finish.

    After imports, the first block defines the parameters for the experiment.
    Next, the TopChef job is sent to the API.
    Finally, the results are printed to the command line.
    """
    from topchef_client import Client
    from time import sleep.

    experiment_parameters = {
        'pulse_time': 10e-9,
        'wait_time': 1e-6,
        'pulse_phase': 0,
        'number_of_repetitions': 5000,
        'type': 'RAMSEY'
    }
    server_url = 'http://localhost:5000'
    service_id = '1e566b07-8011-46f1-b39b-8a8c5700c352'

    client = Client(server_url)
    service = client.services[service_id]
    job = service.new_job(experiment_parameters)

    wait_until_job_done(job)

    print(job.result)

    def wait_until_job_done(job):
        """
        A small subroutine that waits until the job is finished. This can be
        replaced with something more advanced, and is dependent on the
        implementation. The onus is on the consumer of the TopChef API to
        only get results after the job finishes
        """
        while not job.is_complete:
            sleep(0.01)


Details
-------

The base class for running the TopChef client is :class:`Client`. It takes
in the server URL as a parameter

.. code-block:: python

    """
    Small example of a TopChef client
    """
    from topchef_client import Client

    url = 'http://localhost:5000

    client = Client(url)

services are implemented in the :class:`topchef.models.service.Service` class.
