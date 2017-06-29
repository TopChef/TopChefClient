"""
Contains exceptions that can be thrown during the course of executing this
client
"""


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


