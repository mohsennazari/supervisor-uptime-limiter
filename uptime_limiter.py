#!/usr/bin/env python

# Based on Supervisor/Superlance Memmon script.
# https://github.com/supervisor/superlance
# A event listener meant to be subscribed to TICK_60 (or TICK_5)
# events, which restarts any processes that are children of
# supervisord that runs "more than a specified amount of time".
# Works on Linux and OS X (Tiger/Leopard) as far as I know.

# A supervisor config snippet that tells supervisor to use this script
# as a listener is below.
#
# [eventlistener:uptime-limit]
# command=python uptime_limiter.py [options]
# events=TICK_60

doc = """\
uptime_limiter.py [-p processname=time_limit] [-g groupname=time_limit]
          [-a time_limit]
Options:
-p -- specify a process_name=time_limit pair.  Restart the supervisor
      process named 'process_name' when it runs more than time_limit.  
      If this process is in a group, it can be specified using
      the 'group_name:process_name' syntax.
-g -- specify a group_name=time_limit pair.  Restart any process in this group
      when it runs more than time_limit.
-a -- specify a global time_limit.  Restart any child of the supervisord
      under which this runs if it runs more than time_limit.
The -p and -g options may be specified more than once, allowing for
specification of multiple groups and processes.
Any time_limit can be specified as a plain integer (10000) or a
suffix-multiplied integer (e.g. 1h).  Valid suffixes are 's', 'm', 'h' and 'd'.
A sample invocation:
uptime_limiter.py -p program1=200m -p theprog:thegroup=100h -g thegroup=100s -a 1d
"""

import getopt
import os
import sys
import socket

from supervisor import childutils
from supervisor.datatypes import SuffixMultiplier


def usage(exitstatus=255):
    print(doc)
    sys.exit(exitstatus)


def shell(cmd):
    with os.popen(cmd) as f:
        return f.read()


class UptimeLimiter:
    def __init__(self, programs, groups, any):
        self.programs = programs
        self.groups = groups
        self.any = any
        self.rpc = self.getRPCInterface()
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def runforever(self, test=False):
        while 1:
            # we explicitly use self.stdin, self.stdout, and self.stderr
            # instead of sys.* so we can unit test this code
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)

            if not headers['eventname'].startswith('TICK'):
                # do nothing with non-TICK events
                childutils.listener.ok(self.stdout)
                if test:
                    break
                continue

            status = []
            if self.programs:
                keys = sorted(self.programs.keys())
                status.append(
                    'Checking programs %s' % ', '.join(
                        ['%s=%s' % (k, self.programs[k]) for k in keys])
                )

            if self.groups:
                keys = sorted(self.groups.keys())
                status.append(
                    'Checking groups %s' % ', '.join(
                        ['%s=%s' % (k, self.groups[k]) for k in keys])
                )
            if self.any is not None:
                status.append('Checking any=%s' % self.any)

            self.stderr.write('\n'.join(status) + '\n')

            infos = self.rpc.supervisor.getAllProcessInfo()

            for info in infos:
                pid = info['pid']
                name = info['name']
                group = info['group']
                uptime = info['now'] - info['start']
                pname = '%s:%s' % (group, name)

                if not pid:
                    # ps throws an error in this case (for processes
                    # in standby mode, non-auto-started).
                    continue

                for n in name, pname:
                    if n in self.programs:
                        if uptime > self.programs[name]:
                            self.restart(pname, uptime)
                            continue

                if group in self.groups:
                    if uptime > self.groups[group]:
                        self.restart(pname, uptime)
                        continue

                if self.any is not None:
                    if uptime > self.any:
                        self.restart(pname, uptime)
                        continue

            self.stderr.flush()
            childutils.listener.ok(self.stdout)
            if test:
                break
            exit()

    def getRPCInterface(self):
        try:
            rpc = childutils.getRPCInterface(os.environ)
            rpc.supervisor.getAPIVersion()
            return rpc
        except socket.error:
            self.stderr.write('Failed to connect to supervisor server\n')
            raise

    def restart(self, name, uptime):
        self.stderr.write('Restarting %s\n' % name)
        try:
            self.rpc.supervisor.stopProcess(name)
        except Exception as e:
            msg = ('Failed to stop process %s (UPTIME %s), exiting: %s' %
                   (name, uptime, e))
            self.stderr.write(str(msg))
            raise

        try:
            self.rpc.supervisor.startProcess(name)
        except Exception as e:
            msg = ('Failed to start process %s after stopping it, '
                   'exiting: %s' % (name, e))
            self.stderr.write(str(msg))
            raise


seconds_size = SuffixMultiplier({'s': 1,
                                 'm': 60,
                                 'h': 60 * 60,
                                 'd': 60 * 60 * 24
                                 })


def parse_seconds(option, value):
    try:
        seconds = seconds_size(value)
    except:
        print('Unparseable value for time in %r for %s' % (value, option))
        usage()
    return seconds


def parse_namesize(option, value):
    try:
        name, size = value.split('=')
    except ValueError:
        print('Unparseable value %r for %r' % (value, option))
        usage()
    size = parse_seconds(option, size)
    return name, size


help_request = object()  # returned from uptime_limit_from_args to indicate --help


def uptime_from_args(arguments):
    short_args = "hp:g:a:"
    long_args = [
        "help",
        "program=",
        "group=",
        "any="
    ]

    if not arguments:
        return None
    try:
        opts, args = getopt.getopt(arguments, short_args, long_args)
    except:
        return None

    programs = {}
    groups = {}
    any = None

    for option, value in opts:

        if option in ('-h', '--help'):
            return help_request

        if option in ('-p', '--program'):
            name, size = parse_namesize(option, value)
            programs[name] = size

        if option in ('-g', '--group'):
            name, size = parse_namesize(option, value)
            groups[name] = size

        if option in ('-a', '--any'):
            size = parse_seconds(option, value)
            any = size

    uptime_limiter = UptimeLimiter(programs=programs,
                                 groups=groups,
                                 any=any)
    return uptime_limiter


def main():
    uptime_limiter = uptime_from_args(sys.argv[1:])
    if uptime_limiter is help_request:  # --help
        usage(exitstatus=0)
    elif uptime_limiter is None:  # something went wrong
        usage()
    uptime_limiter.runforever()


if __name__ == '__main__':
    main()
