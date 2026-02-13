from abc import ABCMeta, abstractmethod
from typing import Any


class MissionModule(metaclass=ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, 'start') and callable(subclass.start)
            or NotImplemented
        )

    @abstractmethod
    def start(self, options: dict) -> Any:
        """Start the mission module. If you need information to start with, then these can be provided in the
        `options` parameter"""
        raise NotImplementedError("Mission modules must implement `start` method")
