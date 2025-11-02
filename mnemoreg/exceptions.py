class RegistryError(Exception):
    pass


class AlreadyRegisteredError(RegistryError, KeyError):
    pass


class NotRegisteredError(RegistryError, KeyError):
    pass
