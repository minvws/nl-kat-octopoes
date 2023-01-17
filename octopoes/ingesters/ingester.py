import logging
import threading
from pathlib import Path
from typing import Callable, Optional, Any, NoReturn, cast

from graphql import print_schema, GraphQLSchema, GraphQLResolveInfo, GraphQLObjectType

from octopoes import context, utils
from octopoes.connectors.services.xtdb import XTDBSession, XTDBHTTPClient, OperationType
from octopoes.ddl.ddl import SchemaManager
from octopoes.models import Organisation

logger = logging.getLogger(__name__)


class Ingester:

    def __init__(
        self,
        ctx: context.AppContext,
        ingester_id: str,
        organisation: Organisation,
    ):

        self.logger: logging.Logger = logging.getLogger(__name__)

        self.organisation = organisation

        self.ctx = ctx
        self.ingester_id = ingester_id
        self.thread: Optional[utils.ThreadRunner] = None
        self.stop_event: threading.Event = self.ctx.stop_event

        self.xtdb_client = XTDBHTTPClient(self.ctx.config.dsn_xtdb)
        self.schema = GraphQLSchema()
        self.schema_manager = SchemaManager()

    def run_in_thread(
        self,
        func: Callable[[], Any],
        interval: float = 0.01,
        daemon: bool = False,
    ) -> None:
        """Make a function run in a thread, and add it to the dict of threads.

        Args:
            func: The function to run in the thread.
            interval: The interval to run the function.
            daemon: Whether the thread should be a daemon.
        """
        self.thread = utils.ThreadRunner(
            target=func,
            stop_event=self.stop_event,
            interval=interval,
            daemon=daemon,
        )
        self.thread.start()

    def stop(self) -> None:
        """Stop the ingesters."""
        self.thread.join(5)

        self.logger.info("Stopped ingesters: %s", self.ingester_id)

    def run(self) -> NoReturn:
        self.run_in_thread(
            func=self.ingest,
            interval=30,
        )

    def resolve_graphql_type(self, parent_obj: Any, type_name: GraphQLResolveInfo, *args, **kwargs) -> Any:
        print(self.xtdb_client)
        print(type_name)
        return []

    def flatten_ooi_graph(self, ooi: dict) -> str:
        graphql_type = cast(GraphQLObjectType, self.schema.type_map[ooi["object_type"]])
        print(graphql_type)
        nested_keys = [key for key, value in ooi.items() if isinstance(value, dict)]
        for key in nested_keys:
            nested_pk, nested_objects = self.flatten_ooi_graph(ooi[key])
            ooi[key] = nested_pk

        nested_objects.append(ooi)

        return ooi, nested_objects

    def save_origin(self, origin: dict) -> None:
        if origin["origin_type"] == "declaration":
            if len(origin["results"]) != 1:
                raise ValueError("Declaration origin must have exactly one result")
            origin["source"] = origin["results"][0]

    def ingest(self):
        self.logger.info("Ingesting... %s", self.ingester_id)

        # load new schema (from disk for now)
        new_schema = self.schema_manager.load_schema(Path(__name__).parent / "schemas" / "openkat_schema.graphql")
        self.schema_manager.validate(new_schema)

        # compare with previous schema and validate
        ...

        # save to XTDB
        xtdb_session = XTDBSession(self.xtdb_client)
        document = {
            "xt/id": "schema",
            "schema": print_schema(schema_loader.schema),
        }
        xtdb_session.add(
            (OperationType.PUT, document, None)
        )
        xtdb_session.commit()

        print_schema(schema_loader.schema)

        # attach resolvers to schema
        schema_loader.schema.query_type.fields["OOI"].resolve = self.resolve_graphql_type

        # update cached instance
        self.schema = schema_loader.schema

        # ingest normalizer configs
        # ingest bit configs

        # ingest normalizer outputs / origins
        origin = {
            "object_type": "Origin",
            "origin_type": "declaration",
            "results": [
                {
                    "object_type": "Hostname_v1",
                    "network": {
                        "object_type": "Network_v1",
                        "name": "internet",
                    },
                    "name": "openkat.nl",
                },
            ]
        }

        # wait for processing to complete

        # loop(while things to do)
            # execute relational bits
            # wait for processing to complete

        # perform dynamic programming computations
        # - propagate scan profiles

        # persist valid-time, transaction-time pair as consolidated
