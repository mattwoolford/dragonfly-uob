from server.interfaces.MissionModule import MissionModule


class Delivery(MissionModule):

    """

    This mission module controls a sequence where the aircraft can land within 5m-10m of a point of interest,
    release a package, take-off, and then return-to-home (RTH).

    """

    def start(self, options):
        """
        Start the mission module.

        If you need information to start with, then these can be provided in the
        `options` parameter.
        """
        pass
