class VendorInputError(ValueError):
    pass


def _extra(ticket_data):
    extra_data = ticket_data.get("extra_data") or {}
    ticket_data["extra_data"] = extra_data
    return extra_data


def _require(value, field_name):
    if value in [None, ""]:
        raise VendorInputError(f"Missing required field: {field_name}")
    return value


def adapt_ticket_data(vendor, ticket_data):
    key = normalize_vendor_key(vendor)
    if key == "oxxo":
        return adapt_oxxo_ticket(ticket_data)
    if key == "walmart":
        return adapt_walmart_ticket(ticket_data)
    if key == "costco":
        return adapt_costco_ticket(ticket_data)
    raise VendorInputError(f"Unsupported vendor: {vendor}")


def adapt_oxxo_ticket(ticket_data):
    ticket_data = dict(ticket_data)
    ticket_data["vendor"] = "OXXO"
    _require(ticket_data.get("folio"), "folio")
    _require(ticket_data.get("total"), "total")
    _require(ticket_data.get("date"), "date")
    return ticket_data


def adapt_walmart_ticket(ticket_data):
    ticket_data = dict(ticket_data)
    ticket_data["vendor"] = "Walmart"
    extra_data = _extra(ticket_data)
    tr = extra_data.get("tr") or extra_data.get("web_id")
    tc = extra_data.get("tc") or extra_data.get("transaction_number")
    extra_data["tr"] = _require(tr, "tr")
    extra_data["tc"] = _require(tc, "tc")
    _require(ticket_data.get("total"), "total")
    _require(ticket_data.get("date"), "date")
    return ticket_data


def adapt_costco_ticket(ticket_data):
    ticket_data = dict(ticket_data)
    ticket_data["vendor"] = "Costco"
    extra_data = _extra(ticket_data)
    ticket_order = extra_data.get("ticket_order") or extra_data.get("ticket") or extra_data.get("order")
    extra_data["ticket_order"] = _require(ticket_order or ticket_data.get("folio"), "ticket_order")
    ticket_data["folio"] = ticket_data.get("folio") or extra_data["ticket_order"]
    _require(ticket_data.get("total"), "total")
    return ticket_data


def normalize_vendor_key(vendor):
    return str(vendor or "").strip().lower().replace(" ", "_")


def recipe_for_vendor(vendor):
    key = normalize_vendor_key(vendor)
    if key == "oxxo":
        from vendors.oxxo import OxxoRecipe
        return OxxoRecipe
    if key == "walmart":
        from vendors.walmart import WalmartRecipe
        return WalmartRecipe
    if key == "costco":
        from vendors.costco import CostcoRecipe
        return CostcoRecipe
    raise VendorInputError(f"Unsupported vendor: {vendor}")


def ticket_from_cli_args(vendor, args):
    key = normalize_vendor_key(vendor)
    if key == "oxxo":
        return adapt_oxxo_ticket({
            "folio": args.folio,
            "total": args.total,
            "date": args.date,
            "extra_data": {
                "payment_method": args.payment_method,
            },
        })
    if key == "walmart":
        return adapt_walmart_ticket({
            "folio": args.folio,
            "total": args.total,
            "date": args.date,
            "extra_data": {
                "tr": args.tr,
                "tc": args.tc,
                "payment_method": args.payment_method,
            },
        })
    if key == "costco":
        return adapt_costco_ticket({
            "folio": args.ticket_order,
            "total": args.total,
            "date": args.date,
            "extra_data": {
                "ticket_order": args.ticket_order,
                "payment_method": args.payment_method,
            },
        })
    raise VendorInputError(f"Unsupported vendor: {vendor}")
