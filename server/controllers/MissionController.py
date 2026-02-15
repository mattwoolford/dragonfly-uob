from server.interfaces.MissionModule import MissionModule


class MissionController(MissionModule):

    """

    This mission controller acts as a state machine that guides the aircraft through a search and rescue mission.

    """

    def start(self, options):
        """
        Start the mission.

        If you need information to start with, then these can be provided in the
        `options` parameter.
        """
        pass
