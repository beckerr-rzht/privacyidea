"""Store privacyIDEA node in eventcounter table

Revision ID: d756b34061ff
Revises: 3d7f8b29cbb1
Create Date: 2019-09-02 13:59:24.244529

"""
# revision identifiers, used by Alembic.
from sqlalchemy import orm
from sqlalchemy.sql.ddl import CreateSequence

from privacyidea.lib.config import get_privacyidea_node

revision = 'd756b34061ff'
down_revision = '3d7f8b29cbb1'

from alembic import op, context
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class OldEventCounter(Base):
    __tablename__ = 'eventcounter'
    counter_name = sa.Column(sa.Unicode(80), nullable=False, primary_key=True)
    counter_value = sa.Column(sa.Integer, default=0)
    __table_args__ = {'mysql_row_format': 'DYNAMIC'}


class NewEventCounter(Base):
    __tablename__ = 'eventcounter_new'
    id = sa.Column(sa.Integer, sa.Sequence("eventcounter_seq"), primary_key=True)
    counter_name = sa.Column(sa.Unicode(80), nullable=False)
    counter_value = sa.Column(sa.Integer, default=0)
    node = sa.Column(sa.Unicode(255), nullable=False)
    __table_args__ = (sa.UniqueConstraint('counter_name',
                                          'node',
                                          name='evctr_1'),
                      {'mysql_row_format': 'DYNAMIC'})


def dialect_supports_sequences():
    migration_context = context.get_context()
    return migration_context.dialect.supports_sequences


def create_seq(seq):
    if dialect_supports_sequences():
        op.execute(CreateSequence(seq))


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    try:
        # Step 1: Create sequence on Postgres
        seq = sa.Sequence('eventcounter_seq')
        try:
            create_seq(seq)
        except Exception as _e:
            pass
        # Step 2: Create new eventcounter_new table
        op.create_table('eventcounter_new',
                        sa.Column("id", sa.Integer, sa.Sequence("eventcounter_seq"), primary_key=True),
                        sa.Column("counter_name", sa.Unicode(80), nullable=False),
                        sa.Column("counter_value", sa.Integer, default=0),
                        sa.Column("node", sa.Unicode(255), nullable=False),
                        sa.UniqueConstraint('counter_name', 'node', name='evctr_1'),
                        mysql_row_format='DYNAMIC'
                        )
        # Step 3: Migrate data from eventcounter to eventcounter_new
        node = get_privacyidea_node()
        for old_ctr in session.query(OldEventCounter).all():
            new_ctr = NewEventCounter(counter_name=old_ctr.counter_name,
                                      counter_value=old_ctr.counter_value,
                                      node=node)
            session.add(new_ctr)
            print("Migrating counter {!r}={} on node={!r} ...".format(new_ctr.counter_name,
                                                                      new_ctr.counter_value,
                                                                      node))
        session.commit()
        # Step 4: Remove eventcounter
        op.drop_table("eventcounter")
        op.rename_table("eventcounter_new", "eventcounter")
    except Exception as exx:
        session.rollback()
        print("Could not migrate table 'eventcounter'")
        print (exx)

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('evctr_1', 'eventcounter', type_='unique')
    op.drop_column('eventcounter', 'node')
    op.drop_column('eventcounter', 'id')
    # ### end Alembic commands ###