from server.interfaces.MissionModule import MissionModule


class Navigation(MissionModule):

    """

    This mission module guides the aircraft by instructing it to fly to specified coordinates, respecting any defined
    geofencing boundaries.

    """

    def start(self, options):
        """
        Start the mission module.

        If you need information to start with, then these can be provided in the
        `options` parameter.
        """
        pass
