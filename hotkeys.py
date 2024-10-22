import redis
import threading
import time
import argparse
import sys

# Global variable for the sorted set name
hotkeys = "hotkeys"

def check_current_notification_settings(r):
    """
    Check and return the current Redis keyspace event notification configuration.
    """
    try:
        # Get the current notification settings
        current_settings = r.config_get('notify-keyspace-events').get('notify-keyspace-events', '')
        # print(f"Current keyspace/event notification settings: {current_settings}")  # Commented out
        return current_settings
    except Exception as e:
        print(f"Error fetching current notification settings: {e}")
        return ''

def enable_keyspace_notifications(r):
    """
    Enable keyspace notifications on the Redis server.
    """
    try:
        # Enable keyspace notifications (for all key events and expiration)
        r.config_set('notify-keyspace-events', 'KEA')

        # Verify that notifications are enabled
        # current_settings = r.config_get('notify-keyspace-events')  # commented out
        # print(f"Keyspace notification settings enabled: {current_settings}")  # commented out

    except Exception as e:
        print(f"Error enabling keyspace notifications: {e}")

def restore_notification_settings(r, original_settings):
    """
    Restore the original Redis keyspace event notification settings.
    """
    try:
        r.config_set('notify-keyspace-events', original_settings)
        # print(f"Restored keyspace/event notification settings to: {original_settings}")  # Commented out
    except Exception as e:
        print(f"Error restoring notification settings: {e}")

def update_hotkeys(r, key_name):
    """
    Update the sorted set 'hotkeys' based on the key notifications.
    If the key is not in the sorted set, add it with a score of 1.
    If the key is already in the sorted set, increment its score by 1.
    """
    try:
        # Increment the score of the key in the sorted set 'hotkeys'
        r.zincrby(hotkeys, 1, key_name)
        score = r.zscore(hotkeys, key_name)
        # print(f"Updated hotkeys: {key_name} -> {score}")  # Commented out
    except Exception as e:
        print(f"Error updating hotkeys: {e}")

def listen_for_event_space_notifications(r, stop_event, sleep_interval):
    """
    Listen for event space notification events using Redis Pub/Sub.
    This function will terminate when stop_event is set.
    """
    pubsub = r.pubsub()

    # Subscribe to event space notifications (for all events)
    pubsub.psubscribe('__keyevent@0__:*')

    # Process the notifications until the stop event is set
    while not stop_event.is_set():
        message = pubsub.get_message()
        if message and message['type'] == 'pmessage':
            # Extract key name from the event notification data
            key_name = message['data']
            # print(f"Received event notification for: {key_name}")  # commented out
            update_hotkeys(r, key_name)
        time.sleep(sleep_interval)  # Use the user-defined sleep interval (in seconds)

def show_top_keys(r):
    """
    Show the top 20 key names with the highest scores from the sorted set 'hotkeys'.
    """
    try:
        top_keys = r.zrevrange(hotkeys, 0, 19, withscores=True)
        print("\nTop 20 keys with the highest scores:")
        for rank, (key_name, score) in enumerate(top_keys, start=1):
            print(f"{rank}. {key_name}: {score}")
    except Exception as e:
        print(f"Error fetching top keys: {e}")

def custom_usage():
    """
    Custom usage/help message explaining each parameter.
    """
    usage = """
    Usage: python3 hotkeys.py -h <host> -p <port> [-l] [-t <time>] [-T <interval>] [-H | -help | help | ?]

    Parameters:
    -h <host>  : Host (FQDN) of the Redis database (default: localhost).
    -p <port>  : Port of the Redis database (default: 6379).
    -l         : List the current content of hotkeys and exit (optional).
    -t <time>  : Time to operate the script before terminating (default: 10 seconds, range: 1-100) (optional).
    -T <ms>    : Sleep interval in milliseconds between consecutive loops (default: 10ms) (optional).
    -H, -help, help, ? : Display this usage message and exit (optional).
    """
    print(usage)

def parse_arguments():
    """
    Parse command-line arguments and handle help options.
    """
    parser = argparse.ArgumentParser(add_help=False)

    # Mandatory parameters for host (-h) and port (-p)
    parser.add_argument('-h', default='localhost', type=str, help='Host (FQDN) of the Redis database (default: localhost)')
    parser.add_argument('-p', default=6379, type=int, help='Port of the Redis database (default: 6379)')

    # Optional flags and parameters
    parser.add_argument('-l', action='store_true', help='List the current content of hotkeys and exit')
    parser.add_argument('-t', type=int, default=10, help='Time to operate the script before terminating (default: 10 seconds, range: 1-100)')
    parser.add_argument('-T', type=float, default=10, help='Sleep interval in milliseconds between consecutive loops (default: 10 ms)')

    # Check if custom help is requested by handling multiple help options
    parser.add_argument('-H', action='store_true', help='Show help')
    parser.add_argument('-help', action='store_true', help='Show help')
    parser.add_argument('help_arg', nargs='?', default=None, help='Handle ? and help')

    args = parser.parse_args()

    # Display custom help if any help-related flag or argument is detected
    if args.H or args.help or args.help_arg in ['help', '?']:
        custom_usage()
        sys.exit(0)

    # Validate the time (-t) parameter
    if not (1 <= args.t <= 100):
        print("Error: Time (-t) parameter must be between 1 and 100 seconds.")
        sys.exit(1)

    # Convert the sleep interval from milliseconds to seconds
    args.T = args.T / 1000.0

    return args

def main():
    # Parse command-line arguments
    args = parse_arguments()

    try:
        # Connect to the Redis server
        r = redis.StrictRedis(host=args.h, port=args.p, decode_responses=True)

        # If -l flag is provided, list current hotkeys and exit
        if args.l:
            show_top_keys(r)
            sys.exit(0)

        # Delete the sorted set "hotkeys" before starting a new run
        r.delete(hotkeys)
        # print(f"Deleted sorted set '{hotkeys}' before starting a new run.")  # Commented out

        # Check and store the current notification settings
        original_settings = check_current_notification_settings(r)

        # Enable keyspace notifications
        enable_keyspace_notifications(r)

        # Stop event to terminate the listener after the specified time
        stop_event = threading.Event()

        # Start a separate thread to listen for event space notifications
        listener_thread = threading.Thread(target=listen_for_event_space_notifications, args=(r, stop_event, args.T))
        listener_thread.start()

        # Let the listener run for the specified time (-t flag)
        time.sleep(args.t)

        # Signal the listener thread to stop
        stop_event.set()
        listener_thread.join()

        # Show the top 20 keys with the highest scores
        show_top_keys(r)

        # Restore the original keyspace notification settings
        restore_notification_settings(r, original_settings)

        # Delete the hotkeys sorted set after finishing
        r.delete(hotkeys)
        # print(f"Deleted sorted set '{hotkeys}' after the run.")  # Commented out

    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == "__main__":
    main()
