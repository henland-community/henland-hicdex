# dipdup

[![PyPI version](https://badge.fury.io/py/dipdup.svg?)](https://badge.fury.io/py/dipdup)
[![Tests](https://github.com/dipdup-net/dipdup-py/workflows/Tests/badge.svg?)](https://github.com/baking-bad/dipdup/actions?query=workflow%3ATests)
[![Docker Build Status](https://img.shields.io/docker/cloud/build/bakingbad/dipdup)](https://hub.docker.com/r/bakingbad/dipdup)
[![Made With](https://img.shields.io/badge/made%20with-python-blue.svg?)](ttps://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python SDK for developing indexers of [Tezos](https://tezos.com/) smart contracts inspired by [The Graph](https://thegraph.com/).

## Installation

Python 3.8+ is required for dipdup to run.

```shell
$ pip install dipdup
```

## Creating indexer

If you want to see dipdup in action before diving into details you can run a demo project and use it as reference. Clone this repo and run the following command in it's root directory: 

```shell
$ dipdup -c src/hicdex/dipdup.yml run
```

Examples in this guide are simplified Hic Et Nunc demo.

### Write configuration file

Create a new YAML file and adapt the following example to your needs:

```yaml
spec_version: 0.1
package: hicdex

database:
  kind: sqlite
  path: db.sqlite3

contracts:
  HEN_objkts: 
    address: ${HEN_OBJKTS:-KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton}
    typename: hen_objkts
  HEN_minter: 
    address: ${HEN_MINTER:-KT1Hkg5qeNhfwpKW4fXvq7HGZB9z2EnmCCA9}
    typename: hen_minter

datasources:
  tzkt_mainnet:
    kind: tzkt
    url: ${TZKT_URL:-https://staging.api.tzkt.io}

indexes:
  hen_mainnet:
    kind: operation
    datasource: tzkt_mainnet
    contracts:
      - HEN_minter
    handlers:
      - callback: on_mint
        pattern:
          - type: transaction
            destination: HEN_minter
            entrypoint: mint_OBJKT
          - type: transaction
            destination: HEN_objkts
            entrypoint: mint
```

Each handler in index config matches an operation group based on operations' entrypoints and destination addresses in pattern. Matched operation groups will be passed to handlers you define.

### Initialize project structure

Run the following command replacing `config.yml` with path to YAML file you just created:

```shell
$ dipdup -c config.yml init
```

This command will create a new package with the following structure (some lines were omitted for readability):

```
hicdex/
├── handlers
│   ├── on_mint.py
│   └── on_rollback.py
├── hasura-metadata.json
├── models.py
└── types
    ├── hen_minter
    │   ├── storage.py
    │   └── parameter
    │       └── mint_OBJKT.py
    └── hen_objkts
        ├── storage.py
        └── parameter
            └── mint.py
```

`types` directory is Pydantic dataclasses of contract storage and parameter. This directory is autogenerated, you shouldn't modify any files in it. `models` and `handlers` modules are placeholders for your future code and will be discussed later.

You could invoke `init` command on existing project (must be in your `PYTHONPATH`. Do it each time you update contract addresses or models. Code you've wrote won't be overwritten.

### Define models

Dipdup uses [Tortoise](https://tortoise-orm.readthedocs.io/en/latest/) under the hood, fast asynchronous ORM supporting all major database engines. Check out [examples](https://tortoise-orm.readthedocs.io/en/latest/examples.html) to learn how to use is.

Now open `models.py` file in your project and define some models:
```python
from tortoise import Model, fields


class Holder(Model):
    address = fields.CharField(58, pk=True)


class Token(Model):
    id = fields.BigIntField(pk=True)
    creator = fields.ForeignKeyField('models.Holder', 'tokens')
    supply = fields.IntField()
    level = fields.BigIntField()
    timestamp = fields.DatetimeField()
```

### Write event handlers

Now take a look at `handlers` module generated by `init` command. When operation group matching `pattern` block of corresponding handler at config will arrive callback will be fired. This example will simply save minted Hic Et Nunc tokens and their owners to the database:

```python
import hicdex.models as models
from hicdex.types.hen_minter.parameter.mint_objkt import MintOBJKTParameter
from hicdex.types.hen_minter.storage import HenMinterStorage
from hicdex.types.hen_objkts.parameter.mint import MintParameter
from hicdex.types.hen_objkts.storage import HenObjktsStorage
from dipdup.models import TransactionContext, OperationHandlerContext


async def on_mint(
    ctx: OperationHandlerContext,
    mint_objkt: TransactionContext[MintOBJKTParameter, HenMinterStorage],
    mint: TransactionContext[MintParameter, HenObjktsStorage],
) -> None:
    holder, _ = await models.Holder.get_or_create(address=mint.parameter.address)
    token = models.Token(
        id=mint.parameter.token_id,
        creator=holder,
        supply=mint.parameter.amount,
        level=mint.data.level,
        timestamp=mint.data.timestamp,
    )
    await token.save()
```

Handler name `on_rollback` is reserved by dipdup, this special handler will be discussed later.

### Atomicity and persistency

Here's a few important things to know before running your indexer:

* __WARNING!__ Make sure that database you're connecting to is used by dipdup exclusively. When index configuration or models change the whole database will be dropped and indexing will start from scratch.
* Do not rename existing indexes in config file without cleaning up database first, didpup won't handle this renaming automatically and will consider renamed index as a new one.
* Multiple indexes pointing to different contracts must not reuse the same models because synchronization is performed by index first and then by block.
* Reorg messages signal about chain reorganizations, when some blocks, including all operations, are rolled back in favor of blocks with higher weight. Chain reorgs happen quite often, so it's not something you can ignore. You have to handle such messages correctly, otherwise you will likely accumulate duplicate data or, worse, invalid data. By default Dipdup will start indexing from scratch on such messages. To implement your own rollback logic edit generated `on_rollback` handler.

### Run your dapp

Now everything is ready to run your indexer:

```shell
$ dipdup -c config.yml run
```

Parameters wrapped with `${VARIABLE:-default_value}` in config could be set from corresponding environment variables. For example if you want to use another TzKT instance:

```shell
$ TZKT_URL=https://api.tzkt.io dipdup -c config.yml run
```

You can interrupt indexing at any moment, it will start from last processed block next time you run your app again.

Use `docker-compose.yml` included in this repo if you prefer to run dipdup in Docker:

```shell
$ docker-compose build
$ # example target, edit volumes section to change dipdup config
$ docker-compose up hicdex
```

For debugging purposes you can index specific block range only and skip realtime indexing. To do this set `first_block` and `last_block` fields in index config.

### Index templates

Sometimes you need to run multiple indexes with similar configs whose only difference is contract addresses. In this case you can use index templates like this:

```yaml
templates:
  trades:
    kind: operation
    datasource: tzkt_staging
    contracts:
      - <dex>
    handlers:
      - callback: on_fa12_token_to_tez
        pattern:
          - type: transaction
            destination: <dex>
            entrypoint: tokenToTezPayment
          - type: transaction
            destination: <token>
            entrypoint: transfer
      - callback: on_fa20_tez_to_token
        pattern:
          - type: transaction
            destination: <dex>
            entrypoint: tezToTokenPayment
          - type: transaction
            destination: <token>
            entrypoint: transfer

indexes:
  trades_fa12:
    template: trades
    values:
      dex: FA12_dex
      token: FA12_token

  trades_fa20:
    template: trades
    values:
      dex: FA20_dex
      token: FA20_token
```

Template values mapping could be accessed from within handlers at `ctx.template_values`.

### Optional: configure Hasura GraphQL Engine

When using PostgreSQL as a storage solution you can use Hasura integration to get GraphQL API out-of-the-box. Add the following section to your config, Hasura will be configured automatically when you run your indexer.

```yaml
hasura:
  url: http://hasura:8080
  admin_secret: changeme
```

When using included docker-compose example make sure you run Hasura first:

```shell
$ docker-compose up -d hasura
```

Then run your indexer and navigate to `127.0.0.1:8080`.

### Optional: configure logging

You may want to tune logging to get notifications on errors or enable debug messages. Specify path to Python logging config in YAML format at `--logging-config` argument. Default config to start with:

```yml
  version: 1
  disable_existing_loggers: false
  formatters:
    brief:
      format: "%(levelname)-8s %(name)-35s %(message)s"
  handlers:
    console:
      level: INFO
      formatter: brief
      class: logging.StreamHandler
      stream : ext://sys.stdout
  loggers:
    SignalRCoreClient:
      formatter: brief
    dipdup.datasources.tzkt.datasource:
      level: INFO
    dipdup.datasources.tzkt.cache:
      level: INFO
  root:
    level: INFO
    handlers:
      - console
```

## Contribution

To set up development environment you need to install [poetry](https://python-poetry.org/docs/#installation) package manager and GNU Make. Then run one of the following commands at project's root:

```shell
$ # install project dependencies
$ make install
$ # run linters
$ make lint
$ # run tests
$ make test cover
$ # run full CI pipeline
$ make
```

## Contact
* Telegram chat: [@baking_bad_chat](https://t.me/baking_bad_chat)
* Slack channel: [#baking-bad](https://tezos-dev.slack.com/archives/CV5NX7F2L)

## About
This project is maintained by [Baking Bad](https://baking-bad.org/) team.
Development is supported by [Tezos Foundation](https://tezos.foundation/).
