"""
scripts/seed_test_data.py
-------------------------
Sample-data seed script is intentionally disabled.

Sample universities were removed from this repository so the matching
engine only ever considers real institutions registered through
`/register?type=institution`. If you need to populate institutions for
local development, register them through the public registration flow.
"""
import sys

def main() -> int:
    print(
        "seed_test_data.py is disabled.\n"
        "Sample data was removed so the platform only matches real,\n"
        "user-registered institutions. Use /register?type=institution\n"
        "to create institutions for development or demos."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
