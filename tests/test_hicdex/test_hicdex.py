from unittest import IsolatedAsyncioTestCase

import hicdex


class ExampleTest(IsolatedAsyncioTestCase):
    async def test_example(self) -> None:
        assert hicdex
