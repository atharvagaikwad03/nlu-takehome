import os
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()


def createApp():
    app = Flask(__name__)
    #read DATABASE_URL from .env file
    app.config["DATABASE_URL"] = os.environ["DATABASE_URL"]

    from app.db import initPool
    initPool(app) #create the Postgres connection pool

    from app.validation import registerErrorHandlers
    registerErrorHandlers(app) #ValidationError 400 JSON response

    from app.routes import bp
    app.register_blueprint(bp) #register all /property/ routes

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}) #liveness check

    return app
