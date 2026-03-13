from server.interfaces.MissionModule import MissionModule


class Geolocation(MissionModule):

    """

    This mission module implements a methodology to map geographical coordinates onto an image, and therefore can
    identify the geographical coordinates of a selected portion of a given image in a search and rescue context.

    """

    def start(self, options):
        """
        Start the mission module.

        If you need information to start with, then these can be provided in the
        `options` parameter.
        """
        pass
