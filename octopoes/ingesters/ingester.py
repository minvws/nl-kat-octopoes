"""Main processing logic for Octopoes."""
import json
import logging
import threading
from datetime import timezone, datetime
from typing import Callable, Optional, Any, NoReturn, Dict

from graphql import print_schema, GraphQLResolveInfo, GraphQLUnionType, GraphQLObjectType
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
        self.set_resolvers()

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

    def deserialize_obj(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        # remove prefix from fields, but not object_type
        non_prefixed_fields = ["xt/id", "object_type", "primary_key", "human_readable"]
        data = {key.split("/")[1]: value for key, value in obj.items() if key not in non_prefixed_fields}
        data.update({key: value for key, value in obj.items() if key in non_prefixed_fields})
        return data

    def serialize_obj(self, obj: BaseObject) -> Dict[str, Any]:

        pk_overrides = {}
        for key, value in obj:
            if isinstance(value, BaseObject):
                pk_overrides[key] = value.primary_key

        # export model with pydantic serializers
        export: Dict[str, Any] = json.loads(obj.json())
        export.update(pk_overrides)

        # prefix fields, but not object_type
        non_prefixed_fields = ["object_type", "primary_key", "human_readable"]
        for key in non_prefixed_fields:
            export.pop(key)

        export = {f"{obj.object_type}/{key}": value for key, value in export.items()}

        for key in non_prefixed_fields:
            export[key] = getattr(obj, key)

        export["xt/id"] = obj.primary_key
        return export

    def save_obj(self, obj: BaseObject) -> None:
        xtdb_session = XTDBSession(self.xtdb_client)
        for o in obj.sub_objects:
            xtdb_session.add((OperationType.PUT, self.serialize_obj(o), datetime.now(timezone.utc)))
        xtdb_session.commit()

    def resolve_graphql_union(self, data: Any, type_info: GraphQLResolveInfo, union: GraphQLUnionType) -> Any:
        return data["object_type"]

    def resolve_graphql_type(self, parent_obj: Any, type_info: GraphQLResolveInfo, **kwargs: Any) -> Any:
        """Fetch instances of type from XTDB."""

        # outgoing relation
        if parent_obj and type_info.field_name in parent_obj:
            query = """
                {{:query {{:find [(pull ?entity [*])]
                           :where [[?entity :xt/id \"{}\"]] }} }}""".format(
                parent_obj[type_info.field_name]
            )
            results = self.xtdb_client.query(query)
            return self.deserialize_obj(results[0][0])

        if type_info.return_type.of_type == self.current_schema.hydrated_schema.ooi_union_type:
            query = """
                {:query {:find [(pull ?entity [*])]
                         :where [[?entity :object_type]] } }"""
            results = self.xtdb_client.query(query)
            return [self.deserialize_obj(row[0]) for row in results]
        return []

    def set_resolvers(self) -> None:

        # Set resolver for root OOI union type
        self.current_schema.hydrated_schema.schema.query_type.fields["OOI"].resolve = self.resolve_graphql_type

        # Set type resolver for all union types
        for union_type in self.current_schema.hydrated_schema.union_types:
            union_type.resolve_type = self.resolve_graphql_union

        # Set resolver for all object types
        for object_type in self.current_schema.hydrated_schema.object_types:
            for field in object_type.fields.values():
                real_type = field.type.of_type if getattr(field.type, "of_type", None) else field.type
                if isinstance(real_type, GraphQLObjectType):
                    field.resolve = self.resolve_graphql_type
                if isinstance(real_type, GraphQLUnionType):
                    field.resolve = self.resolve_graphql_type

    def update_schema(self, new_schema: SchemaLoader) -> None:
        self.current_schema = new_schema
        self.persist_schema()
        self.dataclass_generator = DataclassGenerator(self.current_schema.openkat_schema)
        self.set_resolvers()

    def ingest(self) -> None:
        """Periodically ingest data."""
        logger.info("Ingesting... %s", self.ingester_id)

        # create node in XTDB
        XTDBHTTPClient(f"{self.ctx.config.dsn_xtdb}").create_node(self.ingester_id)

        # load new current_schema
        new_schema = SchemaLoader()

        # compare with previous current_schema and validate
        if new_schema.openkat_schema_definition != self.current_schema.openkat_schema_definition:
            logger.info("New schema detected, updating")
            self.update_schema(new_schema)

        # ingest normalizer configs
        # ingest bit configs

        # ingest normalizer outputs / origins
        port = {
            "object_type": "IPPort",
            "address": {
                "object_type": "IPv4Address",
                "network": {
                    "object_type": "Network",
                    "name": "internet",
                },
                "address": "1.1.1.1",
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
