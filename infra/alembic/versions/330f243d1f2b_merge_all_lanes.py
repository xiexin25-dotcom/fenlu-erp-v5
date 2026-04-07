"""merge_all_lanes

Revision ID: 330f243d1f2b
Revises: mfg_0007_workstation, mgmt_0007_kpi, plm_0008_quotes_order_lines, scm_0006_stocktake
Create Date: 2026-04-06 21:56:15.571417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '330f243d1f2b'
down_revision: Union[str, None] = ('mfg_0007_workstation', 'mgmt_0007_kpi', 'plm_0008_quotes_order_lines', 'scm_0006_stocktake')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
