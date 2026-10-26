"""Run the loopback server: python -m slothfill"""

import uvicorn

from slothfill.config import HOST, PORT
from slothfill.server import app


def main() -> None:
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
