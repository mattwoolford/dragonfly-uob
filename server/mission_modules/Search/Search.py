from server.interfaces.MissionModule import MissionModule


class Search(MissionModule):

    """
    This mission module implements a path plan methodology with waypoints to search a field (and with the possible
    help of a PLB) so that the mission can find the person in need of rescue.
    """

    def start(self, options):
        """
        Start the mission module.

        If you need information to start with, then these can be provided in the
        `options` parameter.
        """
        pass
