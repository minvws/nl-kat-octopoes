import logging
import threading
from typing import Callable, Optional, Any, NoReturn

from octopoes import context, utils, models
from octopoes.models import Organisation


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
            interval=60,
        )

    def ingest(self):
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
