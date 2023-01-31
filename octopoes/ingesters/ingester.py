"""Main processing logic for Octopoes."""

import logging
import threading
from typing import Callable, Optional, Any, NoReturn

from octopoes.context.context import AppContext
from octopoes.models.organisation import Organisation
from octopoes.utils.thread import ThreadRunner


class Ingester:
    """Main data ingestion unit for an Organization."""

    def __init__(
        self,
        ctx: AppContext,
        ingester_id: str,
        organisation: Organisation,
    ):
        """Initialize the ingester."""
        self.logger: logging.Logger = logging.getLogger(__name__)

        self.organisation = organisation

        self.ctx = ctx
        self.ingester_id = ingester_id
        self.thread: Optional[ThreadRunner] = None
        self.stop_event: threading.Event = self.ctx.stop_event

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

        self.logger.info("Stopped ingesters: %s", self.ingester_id)

    def run(self) -> NoReturn:  # type: ignore
        """Run the ingester."""
        self.run_in_thread(
            func=self.ingest,
            interval=60,
        )

    def ingest(self) -> None:
        """Periodically ingest data."""
        self.logger.info("Ingesting... %s", self.ingester_id)

        # ingest model

        # validate model

        # persist model

        # ingest normalizer configs

        # ingest bit configs

        # ingest normalizer outputs

        # wait for processing to complete

        # loop(while things to do)
        # execute relational bits
        # wait for processing to complete

        # perform dynamic programming computations
        # - propagate scan profiles

        # persist valid-time, transaction-time pair as consolidated
