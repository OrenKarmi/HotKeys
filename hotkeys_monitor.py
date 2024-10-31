import argparse
import redis
import time

# Define the command-to-score mapping
CMD_TO_SCORE = {
    "GET": 1,
    "SET": 2,
    "HSET": 2,
    "HGETALL": 1
}

def monitor_redis(host="localhost", port=6379, password=None, dst_host="localhost", dst_port=6379, dst_password=None, t=10, T=10, s=1, verbose=False, continue_run=False):
    try:
        # Connect to source Redis
        src_client = redis.Redis(host=host, port=port, password=password)

        # Try connecting to destination Redis
        dst_client = None
        try:
            dst_client = redis.Redis(host=dst_host, port=dst_port, password=dst_password)
            dst_client.ping()  # Test connection
            print("Connected to destination Redis database.")
        except redis.ConnectionError:
            print("Destination Redis database not accessible. Using source Redis database.")
            dst_client = src_client  # Fallback to source Redis

        # Calculate sleep duration
        sleep_duration = max(1 - (t / 1000), 0)

        # Loop while within total time
        start_time = time.time()
        while time.time() - start_time < T:
            # Start monitoring
            with src_client.monitor() as monitor:
                # Collect and parse entries within the monitor time window
                end_time = time.time() + (t / 1000)
                for command in monitor.listen():
                    # Parse and print only the 'command' field if it exists
                    if 'command' in command:
                        command_str = command['command']
                        if verbose:
                            print(command_str)
                        
                        # Extract element name (second parameter) and element command (first parameter)
                        command_parts = command_str.split()
                        if len(command_parts) >= 2:
                            element_cmd = command_parts[0]
                            element_name = command_parts[1]
                            
                            # Determine score based on -s parameter
                            if s == 1:
                                score = 1
                            elif s == 2:
                                # Use predefined score or default to 1 if command not in CMD_TO_SCORE
                                score = CMD_TO_SCORE.get(element_cmd, 1)
                            
                            # Increment the score in the sorted set 'hotkeys'
                            dst_client.zincrby("hotkeys", score, element_name)
                            
                            # Print the element_name, element_cmd, and score if verbose
                            if verbose:
                                print(f"Element Name: {element_name}, Command: {element_cmd}, Score: {score}")
                    
                    if time.time() >= end_time:
                        break
            
            # Sleep before the next loop
            time.sleep(sleep_duration)
        
        # Fetch and print the top 20 hotkeys by score from the destination (or source) database
        top_hotkeys = dst_client.zrevrange("hotkeys", 0, 19, withscores=True)
        print("\nTop 20 hotkeys:")
        for hotkey, score in top_hotkeys:
            print(f"{hotkey.decode('utf-8')}: {score}")

        # Delete the hotkeys sorted set unless -c is specified
        if not continue_run:
            dst_client.delete("hotkeys")
            print("\nDeleted 'hotkeys' sorted set.")
    
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redis monitor script with adjustable parameters.")
    parser.add_argument("--host", default="localhost", help="Source Redis database host name")
    parser.add_argument("-p", "--port", type=int, default=6379, help="Source Redis database port")
    parser.add_argument("-a", "--password", default=None, help="Source Redis database password")
    parser.add_argument("--dst_h", default="localhost", help="Destination Redis database host name")
    parser.add_argument("--dst_p", type=int, default=6379, help="Destination Redis database port")
    parser.add_argument("--dst_a", default=None, help="Destination Redis database password")
    parser.add_argument("-t", type=int, default=10, help="Monitor duration in milliseconds")
    parser.add_argument("-T", type=int, default=10, help="Total execution time in seconds")
    parser.add_argument("-s", type=int, default=1, help="Scoring logic: 1 for constant increment, 2 for command-based scoring")
    parser.add_argument("-v", action="store_true", help="Verbose mode. Print monitored command and element details.")
    parser.add_argument("-c", action="store_true", help="Continue mode. Do not delete the 'hotkeys' sorted set at the end of the script.")

    args = parser.parse_args()

    monitor_redis(
        host=args.host,
        port=args.port,
        password=args.password,
        dst_host=args.dst_h,
        dst_port=args.dst_p,
        dst_password=args.dst_a,
        t=args.t,
        T=args.T,
        s=args.s,
        verbose=args.v,
        continue_run=args.c
    )
