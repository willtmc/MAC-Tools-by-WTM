"""
Entry point for running the McLemore Auction Tools application.
This file is used for local development. For production, use Gunicorn with app:create_app().
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
