"""Simulate a device that reports GPS positions to the Wayward API."""

import argparse
import getpass
import os
import random
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--lat", type=float, default=37.7749, help="home latitude")
    parser.add_argument("--lng", type=float, default=-122.4194, help="home longitude")
    parser.add_argument("--count", type=int, default=10, help="number of pings to send")
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between pings")
    parser.add_argument(
        "--jump-after",
        type=int,
        default=None,
        help="after this many pings, jump about 5 km away from home",
    )
    args = parser.parse_args()

    # Read the token from DEVICE_TOKEN or ask for it (hidden input, so it stays out of history)
    token = os.environ.get("DEVICE_TOKEN") or getpass.getpass("Device token: ")
    headers = {"X-Device-Token": token}

    lat, lng = args.lat, args.lng
    for i in range(1, args.count + 1):
        if args.jump_after is not None and i == args.jump_after + 1:
            lat += 0.05  # about 5.5 km north
            print("-- jumping away from home --")
        else:
            lat += random.uniform(-0.0003, 0.0003)  # up to roughly 33 m
            lng += random.uniform(-0.0003, 0.0003)

        response = httpx.post(
            f"{args.url}/pings",
            json={"lat": lat, "lng": lng, "accuracy_m": 10},
            headers=headers,
            timeout=10,
        )
        print(f"ping {i}: lat={lat:.5f} lng={lng:.5f} -> {response.status_code}")
        if response.status_code != 201:
            print(response.text)
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
