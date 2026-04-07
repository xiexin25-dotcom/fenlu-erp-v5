"""Alembic env (async)。

每个 lane 在 versions/ 下用独立子目录存迁移,避免序号冲突。
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context

# 必须 import 所有模型才能让 autogenerate 看到
from packages.shared.db import Base
from packages.shared.models import (  # noqa: F401
    Organization,
    OrganizationType,
    Role,
    Tenant,
    User,
    UserRole,
)
from packages.supply_chain.models import (  # noqa: F401
    Inventory,
    Location,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseReceipt,
    PurchaseReceiptLine,
    PurchaseRequest,
    PurchaseRequestLine,
    RFQ,
    RFQLine,
    StockMove,
    Supplier,
    SupplierProduct,
    SupplierRating,
    SupplierTierChange,
    Warehouse,
)
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 允许 env 变量覆盖
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
