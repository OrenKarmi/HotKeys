# HotKeys
Identifying hotkeys in a database

# Purpose:
**List the keys accessed most often (aka hotkeys).**

# Hot Keys:
A key or small group of keys accessed significantly more frequently than others in the keyspace. Increased traffic on this single key negatively impacts latency and CPU performance on the shard.
Resharding the database will not reduce the load for the shard where the hotkey is stored.

Currently, there is no method for easily tracking hotkeys. The information available with commands-stats, slowlog, and bigkeys will not necessarily indicate hotkeys. Running the monitor command and analyzing the output may point to hotkeys. However, the monitor command may impact the service.

Monitoring the application usage of Redis and identifying hotkeys should be done on the application side using APM tools.

Due to the implications listed below, this tool should be used only as a last resort for tracking hotkeys.

# Product:
Version 1 (to be discontinued): hotkeys.py connects to a Redis database and uses Key-event notifications to track keys’ access rates and list the top ones.  **NOTE: Key-event notifications are triggered only for changes but not reads (CUD, not R) - hence “key reads” will not be counted.
**Version 2 - hotkeys_monitor.py connects to a Redis database and monitors commands executed to detect hotkeys.**
The script uses the MONITOR command to detect the commands executed. To reduce the performance impact of running the MONITOR command - the script runs MONITOR for short intervals (configurable, default 10ms MONITOR interval every 1 second).
The script connects to the “tracked database” and writes the (temporary) output to a destination database. If not provided, the script will use the tracked database to store the hotkeys result (sorted set).

# Permissions:
Permissions are required to access the database and run the MONITOR command. Write permissions required if no destination database credentials are provided. R/W permissions to the destination database required.


# Memory Impact:
The script creates and writes to a sorted set on the database, storing the key names and the number of times accessed. The memory impact is <avg key name size> * <number of keys accessed>
The tracked database has no memory impact if the script has destination database credentials.
#Performance impact:
The short MONITOR intervals are expected to cause a small increase in shards' CPUs. The script sleeps between events tracked to reduce the CPU impact.
If a destination database is NOT provided - the script updates a sorted set named “hotkeys” for all CRUD operations, impacting the tracked database shard CPU where the sorted set is updated (possibly making it a hotkey, too).

# Usage:
python3 monitor_redis.py --host redis_source_host -p 6379 -a source_password \
--dst_h redis_destination_host --dst_p 6380 --dst_a destination_password \
-t 20 -T 60 -s 2 -v -c

Explanation of Each Parameter
--host redis_source_host: Sets the source Redis host to redis_source_host.
-p 6379: Sets the source Redis port to 6379.
-a source_password: Sets the source Redis password to source_password.
--dst_h redis_destination_host: Sets the destination Redis host to redis_destination_host.
--dst_p 6380: Sets the destination Redis port to 6380.
--dst_a destination_password: Sets the destination Redis password to destination_password.
-t 20: Sets each monitor duration to 20 milliseconds.
-T 60: Sets the total script runtime to 60 seconds.
-s 2: Sets scoring logic to 2, where score is based on the command type.
-v: Enables verbose mode to print command details.
-c: Enables continue mode, retaining the hotkeys sorted set at the end of the script.

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
7. Yed0KZps3FtIEvxjNPoDThGFruPWd8UA: 92.0
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

