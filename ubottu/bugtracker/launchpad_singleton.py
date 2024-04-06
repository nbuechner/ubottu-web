from launchpadlib.launchpad import Launchpad

launchpad_instance = None
def get_launchpad():
    global launchpad_instance
    if launchpad_instance is None:
        # Initialize Launchpad instance here.
        # For example, login anonymously for public data access:
        launchpad_instance = Launchpad.login_anonymously('Matrix Ubottu', 'production', version='devel')
    return launchpad_instance