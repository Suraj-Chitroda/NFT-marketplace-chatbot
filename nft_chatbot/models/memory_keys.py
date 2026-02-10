"""
Standard memory keys and types for user memory table.
Used to store user personal details, preferences, and intents.
"""

# Memory types (Memory.memory_type)
MEMORY_TYPE_PERSONAL = "personal"
MEMORY_TYPE_PREFERENCE = "preference"
MEMORY_TYPE_INTENT = "intent"
MEMORY_TYPE_BEHAVIOR = "behavior"

# --- Personal details (memory_type=personal) ---
KEY_DISPLAY_NAME = "display_name"
KEY_TIMEZONE = "timezone"
KEY_LANGUAGE = "language"

# --- Preferences (memory_type=preference) ---
KEY_PREFERRED_VIEW = "preferred_view"       # grid | table
KEY_DETAIL_LEVEL = "detail_level"          # minimal | standard | detailed | full
KEY_RESPONSE_FORMAT = "response_format"    # concise | balanced | detailed
KEY_STYLE_PREFERENCE = "style_preference" # minimal | rich
KEY_PAGE_FORMAT = "page_format"            # e.g. grid-first, table-first (alias for preferred_view in UI terms)

# --- Intents / behavior (memory_type=intent or behavior) ---
KEY_PRIMARY_INTENT = "primary_intent"      # browsing | buying | collecting | research
KEY_INTEREST_COLLECTIONS = "interest_collections"  # comma-separated or JSON
KEY_PRICE_RANGE_INTEREST = "price_range_interest"   # e.g. "under 5 ETH"

# Valid values for preferences (for validation if needed)
VIEW_VALUES = ("grid", "table")
DETAIL_LEVEL_VALUES = ("minimal", "standard", "detailed", "full")
RESPONSE_FORMAT_VALUES = ("concise", "balanced", "detailed")
INTENT_VALUES = ("browsing", "buying", "collecting", "research")
