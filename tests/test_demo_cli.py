from __future__ import annotations

import unittest
from unittest.mock import patch

from model_router import demo_cli


class DemoCliTests(unittest.TestCase):
    def test_main_delegates_to_demo_server(self) -> None:
        with patch("model_router.demo_app.main") as run_demo:
            demo_cli.main()

        run_demo.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
