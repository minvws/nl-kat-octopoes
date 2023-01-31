"""Server that exposes API endpoints for Octopoes."""

import logging
from typing import Any, Dict

import fastapi
import uvicorn

import octopoes
from octopoes import context, models
from octopoes.ingesters import Ingester


class Server:
    """Server that exposes API endpoints for Octopoes."""

    def __init__(
        self,
        ctx: context.AppContext,
        ingesters: Dict[str, Ingester],
    ):
        """Initialize the server."""
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx
        self.ingesters = ingesters

        self.api = fastapi.FastAPI()

        self.api.add_api_route(
            path="/",
            endpoint=self.root,
            methods=["GET"],
            status_code=200,
        )

        self.api.add_api_route(
            path="/health",
            endpoint=self.health,
            methods=["GET"],
            response_model=models.ServiceHealth,
            status_code=200,
        )

    def root(self) -> Any:
        """Root endpoint."""
        return None

    def health(self) -> Any:
        """Health endpoint."""
        response = models.ServiceHealth(
            service="octopoes",
            healthy=True,
            version=octopoes.__version__,
        )

        for service in self.ctx.services.__dict__.values():
            response.externals[service.name] = service.is_healthy()

        return response

    def run(self) -> None:
        """Run the server."""
        uvicorn.run(
            self.api,
            host=self.ctx.config.api_host,
            port=self.ctx.config.api_port,
            log_config=None,
        )
