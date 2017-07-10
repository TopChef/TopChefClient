from topchef_client import ServiceListener
import pytest
import fixtures

ADDRESS = 'localhost'
SERVICE_ID = 'a5b00b5a-6c8b-11e6-b090-843a4b768af4'

class ServiceListenerForTesting(ServiceListener):
    """
    A simple test client that implements the abstract
    client for contacting the topchef server
    """
    def run(self, parameters):
        return parameters

class TestClientConstructor(object):

    def test_constructor(self):
        client = ServiceListenerForTesting(ADDRESS, SERVICE_ID)

        assert client.id == SERVICE_ID
        assert client.address == ADDRESS

class TestCreateNewService(object):
    SERVICE_DESCRIPTION = "TOPCHEF_CLIENT Acceptance Testing Service"
    SERVICE_NAME = "TCAT"
    SERVICE_SCHEMA = fixtures.json_schema()

    def test_create_new_service(self):
        client = ServiceListenerForTesting.new_service(
            description=self.SERVICE_DESCRIPTION, 
            name=self.SERVICE_NAME, 
            job_schema=self.SERVICE_SCHEMA,
            result_schema=self.SERVICE_SCHEMA
        )

        assert isinstance(client, ServiceListenerForTesting)
        assert client.description == self.SERVICE_DESCRIPTION
        assert client.name == self.SERVICE_NAME


