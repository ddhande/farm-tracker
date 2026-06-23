"""App-wide constants and configuration."""

APP_TITLE = "Farm Tracker"
APP_ICON = "🌾"

# Currency / units
CURRENCY = "₹"
AREA_UNIT = "acres"
YIELD_UNIT = "quintal"


def money(value) -> str:
    """Format a number as Indian Rupees."""
    try:
        return f"{CURRENCY}{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return f"{CURRENCY}0.00"


# Expense categories
EXPENSE_CATEGORIES = [
    "Seed",
    "Fertilizer",
    "Pesticide / Insecticide",
    "Diesel / Fuel",
    "Labour",
    "Machinery / Equipment",
    "Irrigation / Water",
    "Transport",
    "Land Rent / Lease",
    "Electricity",
    "Other",
]

# Units used when buying inputs
PURCHASE_UNITS = [
    "kg",
    "quintal",
    "ton",
    "litre",
    "bag",
    "packet",
    "piece",
    "hour",
    "day",
    "trip",
    "acre",
    "lump sum",
]

# Crop lifecycle / SOP stages (standard operating procedure template)
LIFECYCLE_STAGES = [
    "Land Preparation",
    "Ploughing",
    "Sowing / Planting",
    "Germination",
    "First Irrigation",
    "Fertilizer Application",
    "Weeding",
    "Pesticide Spray",
    "Flowering",
    "Grain / Fruit Formation",
    "Maturity",
    "Harvesting",
    "Threshing / Cleaning",
    "Transport to Market",
    "Sale",
]

STAGE_STATUSES = ["Pending", "In Progress", "Done", "Skipped"]

CROP_STATUSES = ["Planned", "Active", "Harvested", "Closed"]
