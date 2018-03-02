# -*- coding: future_fstrings -*-
# Generic linux daemon base class for python 3.x.

import sys, os, time, atexit, signal
import logging
import logging.handlers


class DaemonPython:
    """A generic daemon class.

    Usage: subclass the daemon class and override the run() method."""

    def __init__(self):
        self.pid_file = None
        self.pid = None

    def daemonize(self):
        """Deamonize class. UNIX double fork mechanism."""
        try:
            self.pid = os.fork()
            if self.pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write(f"fork #1 failed: {err}\n")
            sys.exit(1)

        # decouple from parent environment
        # os.chdir('/')
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            self.pid = os.fork()
            if self.pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #2 failed: {0}\n'.format(err))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pid_file
        atexit.register(self.delpid)

        self.pid = str(os.getpid())
        with open(self.pid_file, 'w+') as f:
            f.write(self.pid + '\n')

    def delpid(self):
        os.remove(self.pid_file)

    def start(self):
        """Start the daemon."""

        # Check for a pid_file to see if the daemon already runs
        try:
            with open(self.pid_file, 'r') as pf:
                self.pid = int(pf.read().strip())
        except IOError:
            self.pid = None

        if self.pid:
            message = f"pid file {self.pid_file} already exist.\nDaemon already running?\n"
            sys.stderr.write(message.format())
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """Stop the daemon."""

        # Get the pid from the pidfile
        try:
            with open(self.pid_file, 'r') as pf:
                self.pid = int(pf.read().strip())
        except IOError:
            self.pid = None

        if not self.pid:
            message = f"pid file {self.pid_file} does not exist.\nDaemon not running?\n"
            sys.stderr.write(message)
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(self.pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if e.find("No such process") > 0:
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
            else:
                print(str(err.args))
                sys.exit(1)

    def restart(self):
        """Restart the daemon."""
        self.stop()
        self.start()

    def run(self):
        """You should override this method when you subclass Daemon.

        It will be called after the process has been daemonized by
        start() or restart()."""
