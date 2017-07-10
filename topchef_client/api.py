"""
Base class for the library. Describes the API that should be consumed for
optimal TopChefiness
"""
import requests
from topchef_client.api_model.service import Service
from topchef_client.exceptions import ServiceNotFoundError


class TopChef(object):
    """
    Base class for the API
    """
    def __init__(self, url, http_library=requests):
        """

        :param url: The URL to the TopChef API
        """
        self.url = url
        self.http_library = http_library

    @property
    def services(self):
        """

        :return: The services available on the API
        """
        return _TopChefServicesGetter(self.url, self.http_library)


class _TopChefServicesGetter(object):
    """

    """
    def __init__(self, url, http_library=requests):
        self.url = url
        self.http_library = http_library

    def __getitem__(self, service_uuid):
        """

        :param service_uuid: Return a service by a given UUID
        :return: The service with the given UUID, if it exists
        :raises: :exc:`ServiceNotFoundError`
        """
        service = Service(service_uuid, self.url, self.http_library)

        if not service.does_service_exist:
            self._handle_nonexistent_service(service)

        return service

    def _handle_nonexistent_service(self, service):
        """

        :param service: The non-existent service
        :raises: :exc:`ServiceNotFoundError`
        """
        raise ServiceNotFoundError(
            "A service with UUID %s does not exist at URL %s" % (
                service.service_id, self.url
            )
        )
