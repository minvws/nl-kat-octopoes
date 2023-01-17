import logging.config
import threading
from types import SimpleNamespace

import yaml

import octopoes
from octopoes.config import settings
from octopoes.connectors import services


class AppContext:
    """AppContext allows shared data between modules.

    Attributes:
        config:
            A settings.Settings object containing configurable application
            settings
        services:
            A dict containing all the external services connectors that
            are used and need to be shared in the octopoes application.
        stop_event: A threading.Event object used for communicating a stop
            event across threads.
    """

    def __init__(self) -> None:
        """Initializer of the AppContext class."""
        self.config: settings.Settings = settings.Settings()

        self.logger = logging.getLogger(__name__)

        # Load logging configuration
        try:
            with open(self.config.log_cfg, "r") as log_config:
                logging.config.dictConfig(yaml.safe_load(log_config))
                self.logger.info(f"Configured loggers with config: {self.config.log_cfg}")
        except FileNotFoundError:
            self.logger.warning(f"No log config found at: {self.config.log_cfg}")

        self.katalogus_svc = services.Katalogus(
            host=self.config.dsn_katalogus,
            source=f"octopoes/{octopoes.__version__}",
        )

        # Register external services, SimpleNamespace allows us to use dot
        # notation
        self.services: SimpleNamespace = SimpleNamespace(
            **{
                services.Katalogus.name: self.katalogus_svc,
            }
        )

        self.stop_event: threading.Event = threading.Event()
