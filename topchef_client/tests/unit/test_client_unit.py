from collections import namedtuple
from topchef_client import Client, NetworkError, ValidationError
from topchef_client import ProcessingError
from topchef_client.client import _Job
import pytest
import mock

ADDRESS = 'localhost'
SERVICE_ID = 'a5b00b5a-6c8b-11e6-b090-843a4b768af4'

class ClientForTesting(Client):
    """
    A simple test client that implements the abstract
    client for contacting the topchef server
    """
    def run(self, parameters):
        return parameters

@mock.patch('threading.Thread')
class TestClientConstructor(object):
    
    def test_is_client_abstract(self, mock_thread):
        with pytest.raises(TypeError):
            Client(ADDRESS, SERVICE_ID)
        
        assert not mock_thread.called

    def test_constructor_happy_path(self, mock_thread):
        client = ClientForTesting(ADDRESS, SERVICE_ID)

        assert client.id == SERVICE_ID
        assert client.address == ADDRESS
        
        assert mock_thread.daemon

        assert mock_thread.call_args_list == [
            mock.call(target=client._polling_loop), 
            mock.call(target=client._processing_loop)
        ]

def make_mock_response(json_data, status_code):
    class _MockResponse(object):
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    return _MockResponse(json_data, status_code)

@pytest.fixture
def client():
    return ClientForTesting(ADDRESS, SERVICE_ID)

class TestNewService(object):
    DESCRIPTION = "Service for Unit testing"
    REGISTRATION_SCHEMA = {'type': 'object'}

    NAME = "Unit testing service"

    @mock.patch('requests.post', return_value=make_mock_response({}, 400))
    def test_network_error_raised(self, mock_post, client):
        with pytest.raises(NetworkError):
            client.__class__.new_service(
                ADDRESS, self.NAME, self.DESCRIPTION,
                self.REGISTRATION_SCHEMA
            )
            
        assert mock_post.called

    @mock.patch('requests.post', return_value=make_mock_response({
        'data': {
            'service_details': {
                'id': SERVICE_ID
            }
        }
    }, 201))
    def test_new_service(self, mock_post, client):
        service = client.__class__.new_service(ADDRESS, self.NAME,
            self.DESCRIPTION, self.REGISTRATION_SCHEMA
        )

        assert isinstance(service, client.__class__)
        assert service.id == SERVICE_ID
        assert service.address == ADDRESS

        assert mock_post.called

class TestIsServerAlive(object):

    @mock.patch('requests.get', return_value=make_mock_response({}, 200))
    def test_is_server_alive_true(self, mock_get, client):
        assert client.is_server_alive
        assert mock_get.call_args == mock.call(
            client.address, headers={'Content-Type': 'application/json'})

    @mock.patch('requests.get', return_value=make_mock_response({}, 500))
    def test_is_server_alive_false(self, mock_get, client):
        assert not client.is_server_alive
        assert mock_get.called

class TestJsonGet(object):
    endpoint = 'http://testing/endpoint'

    @mock.patch('requests.get', return_value=make_mock_response({'data': {}}, 200))
    def test_json_get(self, mock_get, client):
        result = client._json_get(self.endpoint)
        
        assert result == {'data': {}}
        assert mock_get.call_args == mock.call(
            self.endpoint, headers={'Content-Type': 'application/json'}
        )

    @mock.patch('requests.get', return_value=make_mock_response({}, 500))
    def test_json_get_kaboom(self, mock_get, client):
        with pytest.raises(NetworkError):
            client._json_get(self.endpoint)

class TestServiceDetails(object):

    @mock.patch('requests.get', return_value=make_mock_response(
        {'data': 'foo'}, 200))
    def test_service_details(self, mock_get, client):
        expected_data = 'foo'
        assert expected_data == client._service_details

@pytest.fixture
def schema():
    SCHEMA = {
        'type': 'object',
        'properties': {
            'value': {
                'type': 'integer'
            }
        }
    }

    return SCHEMA

class TestJobRegistrationSchema(object):

    def test_job_registration_schema(self, client, schema):
        server_response = {'data': {'job_registration_schema': schema}}

        with mock.patch(
            'requests.get', 
            return_value=make_mock_response(server_response, 200)
        ):
            assert schema == client.job_registration_schema

class TestJobResultSchema(object):

    def test_job_result_schema(self, client, schema):
        server_response = {'data': {'job_result_schema': schema}}

        with mock.patch(
            'requests.get',
            return_value=make_mock_response(server_response, 200)
        ):
            assert schema == client.job_result_schema

class TestFirstJobIDInQueue(object):
    def test_first_id(self, client):
        server_response = {
            'data': [{'id': SERVICE_ID}]
        }
        with mock.patch(
            'requests.get', 
            return_value=make_mock_response(server_response, 200)
        ):
            assert SERVICE_ID == client._first_job_id_in_queue

class TestCurrentJob(object):

    @mock.patch('requests.get')
    @mock.patch('topchef_client.Client._first_job_id_in_queue',
        new_callable=mock.PropertyMock, return_value=SERVICE_ID)
    def test_current_job(self, mock_first_id, mock_get, client):
        mock_get.return_value = make_mock_response(
                {'data': {'id': SERVICE_ID}}, 200
        )

        job = client.current_job

        assert isinstance(job, _Job)
        assert job.address == client.address

class TestIsQueueEmpty(object):
    
    @mock.patch('requests.get', return_value=make_mock_response(
        {'data': []}, 200)
    )
    def test_is_queue_empty(self, mock_get, client):
        assert client.is_queue_empty
        assert mock_get.called

    @mock.patch('requests.get', return_value=make_mock_response(
        {'data': [{'id': SERVICE_ID}]}, 200)
    )
    def test_is_queue_empty_false(self, mock_get, client):
        assert not client.is_queue_empty
        assert mock_get.called

class TestCheckinToServer(object):

    @mock.patch('requests.patch', return_value=make_mock_response({}, 500))
    def test_checkin_error(self, mock_get, client):
        with pytest.raises(NetworkError):
            client.check_in_to_server(ADDRESS, SERVICE_ID)

        assert mock_get.call_args == mock.call(
            '%s/services/%s' % (ADDRESS, SERVICE_ID)
        )

    @mock.patch('requests.patch', return_value=make_mock_response({}, 200))
    def test_checkin(self, mock_get, client):
        client.check_in_to_server(ADDRESS, SERVICE_ID)

        assert mock_get.called

