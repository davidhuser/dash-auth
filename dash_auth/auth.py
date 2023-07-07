from __future__ import absolute_import
from abc import ABC, abstractmethod

from dash import Dash
from flask import request
from werkzeug.routing import Map, MapAdapter, Rule


class Auth(ABC):
    def __init__(self, app: Dash, **_kwargs):
        self.app = app
        self._protect()

    def _protect(self):
        """Add a before_request authentication check on all routes.

        The authentication check will pass if either
            * The endpoint is marked as public via
              `app.server.config["PUBLIC_ROUTES"]`
              (PUBLIC_ROUTES should follow the Flask route syntax)
            * The request is authorised by `Auth.is_authorised`
        """

        server = self.app.server

        @server.before_request
        def before_request_auth():
            public_routes = server.config.get("PUBLIC_ROUTES")

            # Convert to MapAdapter if PUBLIC_ROUTES was set manually
            # as a list of routes
            if isinstance(public_routes, list):
                public_routes = Map(
                    [Rule(route) for route in public_routes]
                ).bind("")
                server.config["PUBLIC_ROUTES"] = public_routes

            # Check whether the path matches a public route,
            # or whether the request is authorised
            if (
                (
                    public_routes is not None
                    and public_routes.test(request.path)
                )
                or self.is_authorized()
            ):
                return None

            # Ask the user to log in
            return self.login_request()

    def is_authorized_hook(self, func):
        self._auth_hooks.append(func)
        return func

    @abstractmethod
    def is_authorized(self):
        pass

    @abstractmethod
    def auth_wrapper(self, f):
        pass

    @abstractmethod
    def index_auth_wrapper(self, f):
        pass

    @abstractmethod
    def login_request(self):
        pass


def add_public_routes(app: Dash, routes: list):
    """Add routes to the public routes list.

    The routes passed should follow the Flask route syntax.
    e.g. "/login", "/user/<user_id>/public"
    """

    # Get the current public routes
    public_routes = app.server.config.get("PUBLIC_ROUTES")

    # If it doesn't exist, create it
    if public_routes is None:
        app.server.config["PUBLIC_ROUTES"] = (
            Map([Rule(route) for route in routes]).bind("")
        )

    # If it was set manually as a list of routes, convert to MapAdapter
    # and add new routes
    elif isinstance(public_routes, list):
        app.server.config["PUBLIC_ROUTES"] = (
            Map([Rule(route) for route in public_routes + routes]).bind("")
        )

    # If it exists as a MapAdapter, add new routes
    elif isinstance(public_routes, MapAdapter):
        for route in routes:
            public_routes.map.add(Rule(route))
