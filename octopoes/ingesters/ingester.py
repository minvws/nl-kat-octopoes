"""Main processing logic for Octopoes."""
import json
import logging
import threading
from datetime import timezone, datetime
from typing import Callable, Optional, Any, NoReturn

from graphql import print_schema, GraphQLResolveInfo
from requests import HTTPError

from octopoes.connectors.services.xtdb import XTDBHTTPClient, XTDBSession, OperationType
from octopoes.context.context import AppContext
from octopoes.ddl.dataclasses import DataclassGenerator, BaseObject
from octopoes.ddl.ddl import SchemaLoader
from octopoes.models.organisation import Organisation
from octopoes.utils.thread import ThreadRunner

logger = logging.getLogger(__name__)


class Ingester:
    """Main data ingestion unit for an Organization."""

    def __init__(
        self,
        ctx: AppContext,
        ingester_id: str,
        organisation: Organisation,
    ):
        """Initialize the ingester."""
        self.organisation = organisation

        self.ctx = ctx
        self.ingester_id = ingester_id
        self.thread: Optional[ThreadRunner] = None
        self.stop_event: threading.Event = self.ctx.stop_event

        self.xtdb_client = XTDBHTTPClient(f"{self.ctx.config.dsn_xtdb}/_dev")

        # Try to load the current_schema from XTDB
        self.current_schema = self.load_schema()
        self.dataclass_generator = DataclassGenerator(self.current_schema.openkat_schema)

    def load_schema(self) -> SchemaLoader:
        """Load the current_schema from XTDB."""
        try:
            # current_schema_def = self.xtdb_client.get_entity("schema")
            # current_schema = SchemaLoader(current_schema_def["schema"])
            current_schema = SchemaLoader()
        except HTTPError as exc:
            if exc.response.status_code == 404:
                logger.info("No current_schema found in XTDB, using OpenKAT schema from disk")
                current_schema = SchemaLoader()
            else:
                raise exc
        return current_schema

    def persist_schema(self) -> None:
        """Persist the schema to XTDB."""
        xtdb_session = XTDBSession(self.xtdb_client)
        document = {
            "xt/id": "schema",
            "schema": self.current_schema.openkat_schema_definition,
        }
        xtdb_session.add((OperationType.PUT, document, None))
        xtdb_session.commit()

    def run_in_thread(
        self,
        func: Callable[[], Any],
        interval: float = 0.01,
        daemon: bool = False,
    ) -> None:
        """Make a function run in a thread, and add it to the dict of threads."""
        self.thread = ThreadRunner(
            target=func,
            stop_event=self.stop_event,
            interval=interval,
            daemon=daemon,
        )
        self.thread.start()

    def stop(self) -> None:
        """Stop the ingesters."""
        if self.thread is not None:
            self.thread.join(5)

        logger.info("Stopped ingesters: %s", self.ingester_id)

    def run(self) -> NoReturn:  # type: ignore
        """Run the ingester."""
        self.run_in_thread(
            func=self.ingest,
            interval=30,
        )

    def resolve_graphql_type(self, _: Any, type_info: GraphQLResolveInfo) -> Any:
        """Fetch instances of type from XTDB."""
        print(self.xtdb_client)
        print(type_info)
        return []

    def serialize_obj(self, obj: BaseObject):
        # export model with pydantic serializers
        export = json.loads(obj.json())

        # prefix fields, but not object_type
        export.pop("object_type")
        export = {f"{obj.object_type}/{key}": value for key, value in export.items() if value is not None}

        export["object_type"] = obj.object_type
        export["xt/id"] = obj.primary_key
        return export

    def save_obj(self, obj: BaseObject):
        xtdb_session = XTDBSession(self.xtdb_client)
        for o in obj.sub_objects:
            xtdb_session.add((OperationType.PUT, self.serialize_obj(o), datetime.now(timezone.utc)))
        xtdb_session.commit()

    def ingest(self) -> None:
        """Periodically ingest data."""
        logger.info("Ingesting... %s", self.ingester_id)

        # load new current_schema (from disk for now)
        new_schema = SchemaLoader()

        # compare with previous current_schema and validate
        self.current_schema = new_schema

        self.persist_schema()

        # attach resolvers to current_schema
        self.current_schema.hydrated_schema.schema.query_type.fields["OOI"].resolve = self.resolve_graphql_type

        # ingest normalizer configs
        # ingest bit configs

        self.dataclass_generator = DataclassGenerator(self.current_schema.openkat_schema)

        # ingest normalizer outputs / origins
        port = {
            "object_type": "IPPort",
            "address": {
                "object_type": "IPv4Address",
                "network": {
                    "object_type": "Network",
                    "name": "internet",
                },
                "address": "1.1.1.1"
            },
            "port": 80,
            "state": "open",
            "protocol": "tcp",
        }
        port_ = self.dataclass_generator.parse_obj(port)
        self.save_obj(port_)

        # wait for processing to complete

        # loop(while things to do)
        # execute relational bits
        # wait for processing to complete

        # perform dynamic programming computations
        # - propagate scan profiles

        # persist valid-time, transaction-time pair as consolidated
