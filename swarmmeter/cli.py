import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Swarmmeter CLI")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    status_parser = subparsers.add_parser("status", help="Show system status")
    
    reset_parser = subparsers.add_parser("reset", help="Reset agent")
    reset_parser.add_argument("agent_id", type=str, help="Agent ID to reset")

    quota_parser = subparsers.add_parser("quota", help="Show quota information")
    stats_parser = subparsers.add_parser("stats", help="Show system stats")

    args = parser.parse_args()

    if args.command == "status":
        print("Status: OK")
    elif args.command == "reset":
        print(f"Resetting agent: {args.agent_id}")
    elif args.command == "quota":
        print("Quota: checking...")
    elif args.command == "stats":
        print("Stats: 0 tokens used")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
