import argparse
import json
import sys

from vendors.adapters import VendorInputError, recipe_for_vendor, ticket_from_cli_args


def load_env_if_available():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def add_common_args(parser):
    parser.add_argument("--mode", choices=["explore", "dry-run", "live"], default="explore")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    parser.add_argument("--payment-method", default=None, help="Optional SAT payment method code.")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Vendor learning/manual runner for MX-AutoInvoice recipes."
    )
    subparsers = parser.add_subparsers(dest="vendor", required=True)

    walmart = subparsers.add_parser("walmart", help="Run the Walmart recipe.")
    add_common_args(walmart)
    walmart.add_argument("--tr", help="Walmart ticket number / TR.")
    walmart.add_argument("--tc", help="Walmart transaction number / TC.")
    walmart.add_argument("--folio", default=None, help="Optional folio for logging.")
    walmart.add_argument("--total", type=float, help="Ticket total.")
    walmart.add_argument("--date", help="Purchase date in YYYY-MM-DD format.")

    oxxo = subparsers.add_parser("oxxo", help="Run the OXXO recipe.")
    add_common_args(oxxo)
    oxxo.add_argument("--folio", help="OXXO folio.")
    oxxo.add_argument("--total", type=float, help="Ticket total.")
    oxxo.add_argument("--date", help="Purchase date in YYYY-MM-DD format.")

    costco = subparsers.add_parser("costco", help="Run the Costco Mexico recipe.")
    add_common_args(costco)
    costco.add_argument("--ticket-order", help="Costco Ticket / Orden value.")
    costco.add_argument("--total", type=float, help="Total pagado.")
    costco.add_argument("--date", default=None, help="Optional purchase date in YYYY-MM-DD format.")

    return parser


def main():
    load_env_if_available()
    parser = build_parser()
    args = parser.parse_args()
    worker = None
    try:
        ticket_data = None
        if args.mode != "explore":
            ticket_data = ticket_from_cli_args(args.vendor, args)
        recipe_class = recipe_for_vendor(args.vendor)
        worker = recipe_class(headless=args.headless, mode=args.mode)
        if args.mode == "explore":
            result = worker.explore()
        else:
            result = worker.run(ticket_data)
        if args.json:
            print(json.dumps({"vendor": args.vendor, "mode": args.mode, "result": result}))
        else:
            print(result)
        return 0
    except VendorInputError as e:
        parser.error(str(e))
    finally:
        if worker:
            worker.close()
    return 1


if __name__ == "__main__":
    sys.exit(main())
