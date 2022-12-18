# Supervisor Uptime Limiter

Uptime limiter is a supervisor "event listener" which may be subscribed to
a concrete `TICK_x` event. When it receives a `TICK_x` event (`TICK_60`
is recommended, indicating activity every 60 seconds), it checks that a 
configurable list of programs (or all programs running under supervisor)
are not exceeding a configurable amount of uptime.  If one or more of
these processes is running more than the amount of uptime, this limiter 
will restart the process.

This script is based on [Supervisor/Superlance](https://github.com/supervisor/superlance) Memmon script.

This command is known to work on Linux and Mac OS X, but has not been
tested on other operating systems.

Although this script is an executable program, it isn't useful as a
general-purpose script: it must be run as a `supervisor` event listener
to do anything useful.

This uses Supervisor's XML-RPC interface.  Your `supervisord.conf`
file must have a valid 
[unix_http_server](http://supervisord.org/configuration.html#unix-http-server-section-settings)
or [inet_http_server](http://supervisord.org/configuration.html#inet-http-server-section-settings)
section, and must have an 
[rpcinterface:supervisor](http://supervisord.org/configuration.html#rpcinterface-x-section-settings>)
section.  If you are able to control your `supervisord` instance with
`supervisorctl`, you have already met these requirements.

## Command-Line Syntax

```shell
   $ uptime_limiter [-p processname=time_limit] [-g groupname=time_limit] [-a time_limit]
``` 
```shell
   program:: uptime_limiter
``` 
```shell
   cmdoption:: -h, --help
   
   Show program help.
```
```shell
   cmdoption:: -p <name/time pair>, --program=<name/time pair>

   A name/time pair, e.g. "foo=1h". The name represents the supervisor
   program name that you would like to monitor; the time
   represents the number of seconds (suffix-multiplied using "s", "m", "h" or "d")
   that should be considered "too much".

   This option can be provided more than once to monitor more than one program.

   Programs can be specified using a "namespec", to disambiguate same-named
   programs in different groups, e.g. `foo:bar` represents the program
   `bar` in the `foo` group.
```
```shell
   cmdoption:: -g <name/time pair>, --groupname=<name/time pair>

   A groupname/time pair, e.g. "group=60s". The name represents the supervisor
   group name that you would to monitor; the time
   represents the number of seconds (suffix-multiplied using "s", "m", "h" or "d")
   that should be considered "too much".

   Multiple `-g` options can be provided to monitor more than one group. 
   If any process in this group exceeds the maximum, it will be restarted.
```
```shell
   cmdoption:: -a <time>, --any=<time>

   A size (suffix-multiplied using "s", "m", "h" or "d") that should be
   considered "too much". If any program running as a child of supervisor
   exceeds this maximum, it will be restarted. E.g. 100m.
```

## Configuring Into the Supervisor Config

An ``[eventlistener:x]`` section must be placed in `supervisord.conf`
in order for this script to do its work. See the "Events" chapter in the
Supervisor manual for more information about event listeners.

If the [unix_http_server](http://supervisord.org/configuration.html#unix-http-server-section-settings)
or [inet_http_server](http://supervisord.org/configuration.html#inet-http-server-section-settings)
has been configured to listen on another ip/port or it uses authentication, add the environment variables
`SUPERVISOR_SERVER_URL`, `SUPERVISOR_USERNAME` and `SUPERVISOR_PASSWORD` in the `[eventlistener:x]`
section as shown in Example Configuration 4.

The following examples assume that the script is already on your system `PATH`.

### Example Configuration 1

This configuration causes the script to restart any process which is
a child of `supervisord` running more than 200 seconds.

```ini
[eventlistener:uptime-limiter]
command=uptime_limiter -a 200s
events=TICK_60
```

### Example Configuration 2

This configuration causes the script to restart any process with the
supervisor program name `foo` running more than 15 minutes.

```ini
[eventlistener:uptime-limiter]
command=uptime_limiter -p foo=15m
events=TICK_60
```

### Example Configuration 3

This configuration causes the script to restart any process in the
process group "bar" running more than 1 hour.

```ini
[eventlistener:uptime-limiter]
command=uptime_limiter -g bar=1h
events=TICK_60
```

### Example Configuration 4 (URL, Authentication)

This configuration is the same as the one in `Example Configuration 1` with
the only difference being that the [unix_http_server](http://supervisord.org/configuration.html#unix-http-server-section-settings)
or [inet_http_server](http://supervisord.org/configuration.html#inet-http-server-section-settings)
has been configured to use authentication.

```ini
[eventlistener:uptime-limiter]
command=uptime_limiter -a 200s
environment=SUPERVISOR_SERVER_URL="<url>",SUPERVISOR_USERNAME="<username>",SUPERVISOR_PASSWORD="<password>"
events=TICK_60
```