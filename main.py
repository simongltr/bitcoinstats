import os

import uvicorn


def main(
    port: int = int(os.getenv("API_LISTEN_PORT", "21021")),
    host: str = os.getenv("API_LISTEN_HOST", "127.0.0.1"),
) -> None:
    """Start the uvicorn server."""
    config = uvicorn.Config(
        "app:app",
        port=port,
        host=host,
    )

    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
