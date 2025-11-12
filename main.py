from libprobe.probe import Probe
from lib.check.backups import check_backups
from lib.check.jobs import check_jobs
from lib.version import __version__ as version


if __name__ == '__main__':
    checks = {
        'backups': check_backups,
        'jobs': check_jobs,
    }

    probe = Probe("veeambr", version, checks)

    probe.start()
