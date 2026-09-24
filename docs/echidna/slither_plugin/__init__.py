from .detectors.bait_conservation import BaitConservationCheck

def make_plugin():
    return [BaitConservationCheck], []
