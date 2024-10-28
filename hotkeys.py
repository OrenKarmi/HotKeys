import redis
import threading
import time
import argparse
import sys

# Global variable for the sorted set name
hotkeys = "hotkeys"

# Initialize counters
event_count = 0
update_count = 0

def check_current_notification_settings(r):
    """
    Check and return the current Redis keyspace event notification configuration.
    """
    try:
        current_settings = r.config_get('notify-keyspace-events').get('notify-keyspace-events', '')
        return current_settings
    except Exception as e:
        print(f"Error fetching current notification settings: {e}")
        return ''

def enable_keyspace_notifications(r):
    """
    Enable keyspace notifications on the Redis server.
    """
    try:
        r.config_set('notify-keyspace-events', 'KEA')
    except Exception as e:
        print(f"Error enabling keyspace notifications: {e}")

def restore_notification_settings(r, original_settings):
    """
    Restore the original Redis keyspace event notification settings.
    """
    try:
        r.config_set('notify-keyspace-events', original_settings)
    except Exception as e:
        print(f"Error restoring notification settings: {e}")

def update_hotkeys(dst_r, key_name):
    """
    Update the sorted set 'hotkeys' in the destination Redis database.
    If the key is not in the sorted set, add it with a score of 1.
    If the key is already in the sorted set, increment its score by 1.
    """
    global update_count
    try:
        dst_r.zincrby(hotkeys, 1, key_name)
        update_count += 1
    except Exception as e:
        print(f"Error updating hotkeys: {e}")

def listen_for_event_space_notifications(r, dst_r, stop_event, sleep_interval):
    """
    Listen for event space notification events using Redis Pub/Sub.
    This function will terminate when stop_event is set.
    """
    global event_count
    pubsub = r.pubsub()

    # Subscribe to event space notifications (for all events)
    pubsub.psubscribe('__keyevent@0__:*')

    while not stop_event.is_set():
        message = pubsub.get_message()
        if message and message['type'] == 'pmessage':
            key_name = message['data']
            event_count += 1
            update_hotkeys(dst_r, key_name)
        time.sleep(sleep_interval)  # Use the user-defined sleep interval (in seconds)

def show_top_keys(dst_r):
    """
    Show the top 20 key names with the highest scores from the sorted set 'hotkeys',
    and display additional stats.
    """
    try:
        top_keys = dst_r.zrevrange(hotkeys, 0, 19, withscores=True)
        total_tracked_keys = dst_r.zcard(hotkeys)

        print("\nTop 20 keys with the highest scores:")
        for rank, (key_name, score) in enumerate(top_keys, start=1):
            print(f"{rank}. {key_name}: {score}")

        print("\nScript Execution Stats:")
        print(f"Total events handled: {event_count}")
        print(f"Total unique keys tracked: {total_tracked_keys}")
        print(f"Total updates to hotkeys sorted set: {update_count}")

    except Exception as e:
        print(f"Error fetching top keys: {e}")

def custom_usage():
    """
    Custom usage/help message explaining each parameter.
    """
    usage = """
    Usage: python3 hotkeys.py -h <host> -p <port> [-a <password>] [-dst_h <host>] [-dst_p <port>] [-dst_a <password>] [-l] [-t <time>] [-T <interval>] [-H | -help | help | ?]

    Parameters:
    -h <host>      : Host (FQDN) of the Redis database for listening (default: localhost).
    -p <port>      : Port of the Redis database for listening (default: 6379).
    -a <password>  : Password for the Redis database for listening (optional).
    -dst_h <host>  : Destination Redis database host for storing hotkeys (if omitted, uses the tracked database).
    -dst_p <port>  : Destination Redis database port for storing hotkeys (if omitted, uses the tracked database).
    -dst_a <password> : Password for the destination Redis database (optional).
    -l             : List the current content of hotkeys and exit (optional).
    -t <time>      : Time to operate the script before terminating (default: 10 seconds, range: 1-100).
    -T <ms>        : Sleep interval in milliseconds between consecutive loops (default: 10 ms).
    -H, -help, help, ? : Display this usage message and exit.
    """
    print(usage)

def parse_arguments():
    """
    Parse command-line arguments and handle help options.
    """
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument('-h', default='localhost', type=str, help='Host (FQDN) of the Redis database (default: localhost)')
    parser.add_argument('-p', default=6379, type=int, help='Port of the Redis database (default: 6379)')
    parser.add_argument('-a', type=str, help='Password for the Redis database (optional)')
    parser.add_argument('-dst_h', type=str, help='Destination Redis database host (default: same as listening database)')
    parser.add_argument('-dst_p', type=int, help='Destination Redis database port (default: same as listening database)')
    parser.add_argument('-dst_a', type=str, help='Password for the destination Redis database (optional)')
    parser.add_argument('-l', action='store_true', help='List the current content of hotkeys and exit')
    parser.add_argument('-t', type=int, default=10, help='Time to operate the script before terminating (default: 10 seconds, range: 1-100)')
    parser.add_argument('-T', type=float, default=10, help='Sleep interval in milliseconds between consecutive loops (default: 10 ms)')

    parser.add_argument('-H', action='store_true', help='Show help')
    parser.add_argument('-help', action='store_true', help='Show help')
    parser.add_argument('help_arg', nargs='?', default=None, help='Handle ? and help')

    args = parser.parse_args()

    if args.H or args.help or args.help_arg in ['help', '?']:
        custom_usage()
        sys.exit(0)

    if not (1 <= args.t <= 100):
        print("Error: Time (-t) parameter must be between 1 and 100 seconds.")
        sys.exit(1)

    args.T = args.T / 1000.0

    return args

def main():
    global event_count, update_count

    args = parse_arguments()

    try:
        # Connect to the Redis database for listening
        connection_params = {
            "host": args.h,
            "port": args.p,
            "decode_responses": True
        }
        if args.a:
            connection_params["password"] = args.a
        r = redis.StrictRedis(**connection_params)

        # Determine the destination Redis database for storing hotkeys
        # Fallback to the listening database if -dst_h or -dst_p is not provided
        if args.dst_h is None or args.dst_p is None:
            dst_r = r
        else:
            dst_connection_params = {
                "host": args.dst_h,
                "port": args.dst_p,
                "decode_responses": True
            }
            if args.dst_a:
                dst_connection_params["password"] = args.dst_a
            dst_r = redis.StrictRedis(**dst_connection_params)

        # If -l flag is provided, list current hotkeys in the destination and exit
        if args.l:
            show_top_keys(dst_r)
            sys.exit(0)

        # Delete the sorted set "hotkeys" in the destination database before starting, ignoring errors
        try:
            dst_r.delete(hotkeys)
        except Exception:
            pass

        # Check and store the current notification settings for the listening Redis database
        original_settings = check_current_notification_settings(r)

        # Enable keyspace notifications on the listening Redis database
        enable_keyspace_notifications(r)

        # Stop event to terminate the listener after the specified time
        stop_event = threading.Event()

        # Start a separate thread to listen for event space notifications
        listener_thread = threading.Thread(target=listen_for_event_space_notifications, args=(r, dst_r, stop_event, args.T))
        listener_thread.start()

        # Let the listener run for the specified time (-t flag)
        time.sleep(args.t)

        # Signal the listener thread to stop
        stop_event.set()
        listener_thread.join()

        # Show the top 20 keys with the highest scores
        show_top_keys(dst_r)

        # Restore the original keyspace notification settings for the listening Redis database
        restore_notification_settings(r, original_settings)

        # Delete the hotkeys sorted set in the destination database after finishing, ignoring errors
        try:
            dst_r.delete(hotkeys)
        except Exception:
            pass

    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == "__main__":
    main()
