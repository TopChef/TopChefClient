# TopChefClient

Contains a client written in Python to consume
the [TopChef](https://github.com/TopChef/TopChef) API.

## Project Status

[![Build Status](
    https://travis-ci.org/TopChef/TopChefClient.svg?branch=master)](
    https://travis-ci.org/TopChef/TopChefClient
)

[![Requirements Status](
https://requires.io/github/TopChef/TopChefClient/requirements.svg?branch=master
)](
https://requires.io/github/TopChef/TopChefClient/requirements/?branch=master)

## Dependencies

The dependencies for this project are given in the ``requirements.txt`` file.
This project relies chiefly on the 
[requests](http://docs.python-requests.org/en/master/) library for sending HTTP
requests to the API. The [six](https://pypi.python.org/pypi/six) library is
a Python 2 - Python 3 compatibility library. It makes creating 
[abstract base classes](https://docs.python.org/2/library/abc.html) much easier.

Python versions greater than 2.6 are supported.

## Project Management

This project is managed on [Waffle IO](https://waffle.io/TopChef/TopChef).
The team throughput is shown below

[![Throughput Graph](
    https://graphs.waffle.io/TopChef/TopChef/throughput.svg
)](https://waffle.io/TopChef/TopChef/metrics/throughput)

## Installation

Install the dependencies by running

```bash
pip install -r requirements.txt
```

Then

```bash
python setup.py install
```


## Usage

After installation, import ``Client`` from the ``topchef_client`` library.
``Client`` is an abstract base class that must have its ``run`` method
implemented prior to use. The run method takes in a dictionary of parameters
and it must return a dictionary of result values.

The input parameters satisfy the service's ``job_registration_schema``. The 
result dictionary must satisfy the service's ``job_result_schema``.


### Example

Consider a service that takes in a number and adds ``1`` to it. Let the
argument be constrained between ``1`` and ``10``. The JSON schema to express
this is

```json
    {
        "type": "integer",
        "minimum": 1,
        "maximum": 10
    }
```

This matches any integer between 1 and 10.

Considering that we're using JSON, it may make sense to wrap the parameters
that we want into a JS object. This would provide a context for our values,
making the code we use much more self-documenting. If we want to add parameters
later, then we can do that much more easily when the object is wrapped. The
JSON schema we'll use for input is therefore

```json
    {
        "type": "object"
        "properties": 
        {
            "value": 
            {
                "type": "integer",
                "minimum": 1,
                "maximum": 10
            }
        }
    } 
```

#### A possible subclass

```python
    from topchef_client import Client

    class AddOne(Client):
        def run(self, parameters):
            result = parameters['value'] + 1
            return {'value': result}
```

The client takes care of validating the input against the input schema, so we
can be confident in extracting the ``'value'`` key out of the parameter
dictionary without worrying about ``KeyError`` being thrown. However, the onus
is on the run method to return a dictionary that is compliant with the result
schema. Failure to do so will result in a ``ProcessingError`` being thrown.

#### Construction

Service IDs can be obtained from the API
by sending a ``GET`` request to the ``/services`` endpoint. The default
constructor takes in the address of the TopChef API and the service ID.

#### Alternative: Register Service

The service can also be registered as a new service at runtime. The classmethod
``Client.register_service``` takes in an address, a service name, 
description, and the service schemas. The method then ``POST``s to the API in
order to register a service with a new service ID.

#### Starting The Client

At runtime, the client launches a polling thread and a processing thread. The
polling thread is responsible for sending a ``PATCH`` request to the API to let
the API know that the client is alive and accepting jobs. The second thread is
a processing thread which checks the ``/services/<service_id>/queue`` for
jobs that have not yet been processed. If it finds one, it executes the job.

Both of these threads are daemonic. If only daemonic threads remain in a Python
program, Python will shut the program down. In our case, instantiating 
``AddOne`` and calling the instance's ``start`` method will start both threads.
After starting, a blocking operation needs to be included somewhere that will
pause the main threads while the client's two threads get to work. An example
of such a method is given in the complete listing below. This code will run
a service.

```python

    from topchef_client import Client
    import time

    class AddOne(Client):
        def run(self, parameters):
            return {'value': parameters['value'] + 1}

    service_address = 'http://localhost'

    service_id = '912a5684-7174-11e6-88ce-3c970e7271f5'


    if __name__ == '__main__':
        service = AddOne(service_address, service_id)
        
        service.start()

        while True:
            time.sleep(3600)
```

## Authors

* Michal Kononenko (@MichalKononenko)
* Thomas Alexander (@whitewhim2718)
