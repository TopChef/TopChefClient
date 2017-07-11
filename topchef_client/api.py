"""
Base class for the library. Describes the API that should be consumed for
optimal TopChefiness.
"""
import requests
from abc import ABCMeta, abstractmethod
from six import add_metaclass
from copy import deepcopy
from topchef_client.models.service import Service
from topchef_client.exceptions import ServiceNotFoundError


class Client(object):
    """
    The main entry point for the TopChef API.
    This is the base object which will be used to communicate with the API.
    """

    CONTENT_TYPE_HEADER = {'Content-Type': 'application/json'}

    def __init__(self, url, http_library=requests):
        """

        :param str url: The base URL to the TopChef API
        :param mod http_library: The library to use for making HTTP
            requests. By default, this is ``requests``, but it can be
            overwritten for testing
        """
        self.url = url
        self._http_library = http_library

    @property
    def http_library(self):
        """
        Provides read-only access to the library used to make HTTP calls

        :return: The current HTTP library
        """
        return self._http_library

    @property
    def services(self):
        """
        :return: The services available on the API.
        :rtype: Client.AbstractServicesGetter
        """
        return self._TopChefServicesGetter(self)

    @property
    def services_url(self):
        """

        :return: The URL where broad information is kept on the services
            registered with the API
        """
        return '{0}/services'.format(self.url)

    @add_metaclass(ABCMeta)
    class AbstractServicesGetter(object):
        """
        Describes the interface for getting services from the TopChef API.
        This type should behave in a similar way to that of the ``dict``
        type.

        One MUST be allowed to get services using the ``__getitem__``
        method. Iteration should also be allowed over all services on the API.
        """
        @abstractmethod
        def __getitem__(self, service_uuid):
            """

            :param str or UUID service_uuid: The UUID matching that of the
                service.
            :return: The service with ``service_id`` matching that of the UUID
            :rtype: :class:`Service`
            :raises: :exc:`ServiceNotFoundError` if the service cannot be found
            """
            raise NotImplementedError()

        @abstractmethod
        def __len__(self):
            """

            :return: The number of services registered on this API
            :rtype: int
            """
            raise NotImplementedError()

        @abstractmethod
        def __iter__(self):
            """

            :return: An iterator over all the services registered on the API
            """
            raise NotImplementedError()

        @abstractmethod
        def __next__(self):
            """

            :return: The next service to be iterated over
            """
            raise NotImplementedError()

        @abstractmethod
        def __dict__(self):
            """

            :return: All the services registered with the API, returned in the
             form ``{service_id: Service}``.
            """
            raise NotImplementedError()

    class _TopChefServicesGetter(AbstractServicesGetter):
        """
        Provides a means of getting services, implementing
        ``AbstractServicesGetter``
        """

        def __init__(self, client):
            """

            :param Client client: The TopChef API client to which this instance
                is attached
            """
            self.client = client
            self.http_headers = deepcopy(self.client.CONTENT_TYPE_HEADER)

            self._last_iterated_index = 0

        def __getitem__(self, service_uuid):
            """

            :param service_uuid: Return a service by a given UUID
            :return: The service with the given UUID, if it exists
            :rtype: :class:`Service`
            :raises: :exc:`ServiceNotFoundError`
            """
            service = Service(
                service_uuid, self.client.url, self.client.http_library
            )

            if not service.does_service_exist:
                self._handle_nonexistent_service(service)

            return service

        def __len__(self):
            """

            :return: The number of services on the API
            """
            return len(self._data_from_services_request)

        def __iter__(self):
            """

            :return: Since this type is iterable, return itself
            """
            return self

        def __next__(self):
            """

            :return: The next service in the mapping of iterables
            """
            if self._last_iterated_index == len(self):
                self._handle_iterator_stop()
            else:
                data = self._data_from_services_request[
                    self._last_iterated_index
                ]
                self._last_iterated_index += 1
                return Service(
                    data['id'], self.client.url, self.client.http_library
                )

        def __dict__(self):
            """

            :return: All the services, collected into a dictionary of the
                form ``{service_id: service}
            :rtype: dict
            """
            return {service.service_id: service for service in self}

        @property
        def content_type_header(self):
            """

            :return: The header indicating that the HTTP request to the
            services endpoint is to be made in JSON
            """
            return self.client.CONTENT_TYPE_HEADER

        @property
        def _http_library(self):
            """

            :return: The library to use for HTTP requests
            """
            return self.client.http_library

        @property
        def _services_url(self):
            """

            :return: The URL to which requests for services are to be made
            """
            return self.client.services_url

        def _handle_nonexistent_service(self, service):
            """

            :param service: The non-existent service
            :raises: :exc:`ServiceNotFoundError`
            """
            raise ServiceNotFoundError(
                "A service with UUID %s does not exist at URL %s" % (
                    service.service_id, self.client.url
                )
            )

        @property
        def _data_from_services_request(self):
            """

            :return: The parsed JSON from the request to the services
                endpoint, containing just the data
            :rtype: dict
            """
            response = self._http_library.get(
                self._services_url, headers=self.content_type_header
            )

            data = response.json()['data']
            return data

        def _handle_iterator_stop(self):
            """
            Clear the last iterated index and throw ``StopIteration``
            """
            self._last_iterated_index = 0
            raise StopIteration()
