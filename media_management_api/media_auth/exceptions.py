import json


class MediaAuthException(Exception):
    def __init__(self, *args):
        super(MediaAuthException, self).__init__(*args)
        self.msg = args[0]

    def as_json(self):
        return json.dumps({"error": self.msg})


class InvalidApplicationError(MediaAuthException):
    pass


class InvalidTokenError(MediaAuthException):
    pass


class InvalidScopeError(MediaAuthException):
    pass
