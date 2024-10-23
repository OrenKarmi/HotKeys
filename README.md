# HotKeys
Identifying hotkeys in a database

# Purpose:
**hotkeys.py lists the keys accessed most often (aka hotkeys).**

# Hot Keys:
A key or small group of keys accessed significantly more frequently than others in the keyspace. Increased traffic on this single key negatively impacts latency and CPU performance on the shard.
Resharding the database will not reduce the load for the shard where the hotkey is stored.

Currently, there is no method for easily tracking hotkeys. The information available with commands-stats, slowlog, and bigkeys will not necessarily indicate hotkeys. Running the monitor command and analyzing the output may point to hotkeys. However, the monitor command may impact the service.

Monitoring the application usage of Redis and identifying hotkeys should be done on the application side using APM tools.

Due to the implications listed below, this tool should be used only as a last resort for tracking hotkeys.

# Product:
**hotkeys.py connects to a Redis database and uses Key-event notifications to track keys’ access rates and list the top ones.**

# Permissions:
Permissions are required to access the database, subscribe to key-event notifications, and write to/ read from the database.
# Memory Impact:
The script creates and writes to a sorted set on the database, storing the key names and the number of times accessed. The memory impact is <avg key name size> * <number of keys accessed>
#Performance impact:
The script updates the sorted set named "hotkeys" for all CRUD operations, impacting the shard CPU where the sorted set is updated (possibly making it a hotkey too). The script sleeps between events tracked to reduce the CPU impact.

# Usage:
Usage: python3 hotkeys.py -h <host> -p <port> [-l] [-t <time>] [-T <interval>] [-H | -help | help | ?]
Parameters:
-h <host>: Host (FQDN) of the Redis database (default: localhost).
-p <port>: Port of the Redis database (default: 6379).
-l       : List the current content of hotkeys and exit (optional).
-t <time>: Time to operate the script before terminating (default: 10 seconds, range: 1-100) (optional).
-T <ms>  : Sleep interval in milliseconds between consecutive loops (default: 10ms) (optional).
-H, -help, help, ? : Display this usage message and exit (optional).

# Outcome:
**The script lists the keys accessed the most and the number of times accessed.**
**NOTE: The access rate output indicates only a fraction of the number of times a key was accessed.** This is because the script receives no key-event notifications during the interleaving sleep intervals (configurable, default 10ms).

# Sample output:
Top 20 keys with the highest scores:
1. vDmaumeF4DDwJmGI2wYmYHUqIuCgKlxw: 161.0
2. YHQq0Uss1e0wo7noUff2pdgxon0RCwBc: 146.0
3. vZxk93HtySxlWeaDg0EGRJNfFR1SF0Jw: 141.0
4. 4mOykuOBL80A4bWUSBGvAHdXL7FShddM: 136.0
5. 9DvyTZdGslaqW8x5BtUf1z0LK5fDj4Jz: 126.0
6. vf8gY99xjEM8omHcG7NQ9rOHX95v0iLG: 124.0
7. hotkeys: 114.0
8. NX45ge1gnjkNdhm8gAs0vfwHelqkH5Sn: 58.0
9. 8xhNJOTC1qS7IoUgNSPhSb34mk68Ejbh: 56.0
10. jkNcWzuI6DL6ouRYQqH505C3G6gc7fuk: 49.0
11. 3ONQObOz25tBcNkcrUkyIoLmcX5ez0TH: 49.0
12. zzdw77QPSx5nb5ster7jrZT2tmyu7IZY: 1.0
13. zxUsfGefBf0jBG8lhI91IwsoO2rPiJsq: 1.0
14. zwi0baH0zXX9aH2MtL9my5rxTzIO9aRb: 1.0
15. zqsZchmgi8o7lgHaHiXanVP9FjNzlGum: 1.0
16. zkwTY9fHfYa1HgJwy6PnzSNCdRL2mM8c: 1.0
17. zUzQCIA7dlYZFLcsM2TglJYjN8KvOPbE: 1.0
18. zHYeCaTh3owMDuzUTpo32ZnObc5qPrrh: 1.0
19. z8fxXv6ZyFESopirRpZjdjZ2WZyiZQ77: 1.0
20. ybXGKFqCrFXrwxMHo9rZZGiNQKoswL6B: 1.0

