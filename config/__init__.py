from typing import Any


class Config:
    def __init__(self):
        pass

    def get(self, var_name: str) -> Any:
        return self.__dict__.get(var_name)


CONFIG = Config()
