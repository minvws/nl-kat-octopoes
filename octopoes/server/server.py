"""Server that exposes API endpoints for Octopoes."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

import uvicorn
from fastapi import FastAPI, status
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
from graphql import print_schema, graphql_sync
from pydantic import BaseModel

from octopoes.context.context import AppContext
from octopoes.ingesters.ingester import Ingester
from octopoes.models.health import ServiceHealth
from octopoes.models.ingester import Ingester as IngesterModel
from octopoes.version import version


class GraphqlRequest(BaseModel):
    """Request body for graphql queries."""

    operationName: Optional[str]
    query: str


class Server:
    """Server that exposes API endpoints for Octopoes."""

    def __init__(
        self,
        ctx: AppContext,
        ingesters: Dict[str, Ingester],
    ):
        """Initialize the server."""
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: AppContext = ctx
        self.ingesters = ingesters

        self.api = FastAPI()

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
            response_model=ServiceHealth,
            status_code=200,
        )

        self.api.add_api_route(
            path="/ingesters",
            endpoint=self.get_ingesters,
            methods=["GET"],
            response_model=List[IngesterModel],
            status_code=200,
        )

        self.api.add_api_route(
            path="/{ingester_id}/graphiql",
            endpoint=self.get_graphiql,
            methods=["GET"],
            response_class=HTMLResponse,
            status_code=200,
        )

        self.api.add_api_route(
            path="/{ingester_id}/graphql",
            endpoint=self.post_graphql,
            methods=["POST"],
            response_class=JSONResponse,
            status_code=200,
        )

        self.api.add_api_route(
            path="/{ingester_id}/graphql",
            endpoint=self.get_graphql_schema,
            methods=["GET"],
            response_class=PlainTextResponse,
            status_code=200,
        )

        self.api.add_api_route(
            path="/{ingester_id}/objects/{object_id}",
            endpoint=self.get_object,
            methods=["GET"],
            response_class=JSONResponse,
            status_code=200,
        )

    def root(self) -> Any:
        """Root endpoint."""
        return None

    def health(self) -> Any:
        """Health endpoint."""
        response = ServiceHealth(
            service="octopoes",
            healthy=True,
            version=version,
        )

        for service in self.ctx.services.__dict__.values():
            response.externals[service.name] = service.is_healthy()

        return response

    def get_ingesters(self) -> Any:
        """List ingesters."""
        return [IngesterModel(id=ingester) for ingester in self.ingesters.keys()]

    def get_graphql_schema(self, ingester_id: str) -> Any:
        """Serve graphql schema."""
        if ingester_id not in self.ingesters:
            return status.HTTP_404_NOT_FOUND

        return print_schema(self.ingesters[ingester_id].current_schema.hydrated_schema.schema)

    def get_object(self, ingester_id: str, object_id: str) -> Any:
        """Get an object."""
        if ingester_id not in self.ingesters:
            return status.HTTP_404_NOT_FOUND

        return self.ingesters[ingester_id].object_repository.get(object_id)

    def get_graphiql(self, ingester_id: str) -> Any:
        """Serve graphiql frontend."""
        if ingester_id not in self.ingesters:
            return status.HTTP_404_NOT_FOUND

        # load template from disk
        graphiql_template = Path(__file__).parent / "static" / "graphiql.html"
        with open(graphiql_template, "r") as graphiql_html:
            template = graphiql_html.read()
            return template.replace("{{ingester_id}}", ingester_id)

    def post_graphql(self, ingester_id: str, request_body: GraphqlRequest) -> Any:
        """Execute grqpql query."""
        if ingester_id not in self.ingesters:
            return status.HTTP_404_NOT_FOUND

        result = graphql_sync(self.ingesters[ingester_id].current_schema.hydrated_schema.schema, request_body.query)
        return result.formatted

    def run(self) -> None:
        """Run the server."""
        uvicorn.run(
            self.api,
            host=self.ctx.config.api_host,
            port=self.ctx.config.api_port,
            log_config=None,
        )
