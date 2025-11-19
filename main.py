from libprobe.probe import Probe
from lib.check.backups import CheckBackups
from lib.check.malware_events import CheckMalwareEvents
from lib.version import __version__ as version


if __name__ == '__main__':
    checks = (
        CheckBackups,
        CheckMalwareEvents,
    )

    probe = Probe("veeambr", version, checks)

    probe.start()
