from libprobe.probe import Probe
from lib.check.backups import CheckBackups
from lib.version import __version__ as version


if __name__ == '__main__':
    checks = (
        CheckBackups,
    )

    probe = Probe("veeambr", version, checks)

    probe.start()
