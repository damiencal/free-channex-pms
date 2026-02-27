"""create accounting tables and add reconciliation_status to Phase 2 tables

Revision ID: 003
Revises: 002
Create Date: 2026-02-27

Creates all Phase 3 tables in a single migration so that Wave-2 plans
(03-03, 03-04, 03-05) can run in parallel without migration file conflicts.

Tables created:
  - accounts (with chart of accounts seed data)
  - journal_entries
  - journal_lines
  - expenses (stub table — ORM model created in 03-03)
  - loans (stub table — ORM model created in 03-04)
  - reconciliation_matches (stub table — ORM model created in 03-05)

Columns added to existing tables:
  - bookings.reconciliation_status
  - bank_transactions.reconciliation_status
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

# fmt: off
CHART_OF_ACCOUNTS = [
    {"number": 1010, "name": "Mercury Checking",          "account_type": "asset",     "is_active": True},
    {"number": 1020, "name": "Accounts Receivable",       "account_type": "asset",     "is_active": True},
    {"number": 2010, "name": "Unearned Revenue",          "account_type": "liability", "is_active": True},
    {"number": 2100, "name": "RV Purchase Loan Payable",  "account_type": "liability", "is_active": True},
    {"number": 2110, "name": "Working Capital Loan Payable", "account_type": "liability", "is_active": True},
    {"number": 2200, "name": "Owner Reimbursable",        "account_type": "liability", "is_active": True},
    {"number": 3000, "name": "Owner Equity",              "account_type": "equity",    "is_active": True},
    {"number": 4000, "name": "Rental Income",             "account_type": "revenue",   "is_active": True},
    {"number": 4010, "name": "Promotional Discounts",     "account_type": "revenue",   "is_active": True},
    {"number": 5010, "name": "Platform Fees",             "account_type": "expense",   "is_active": True},
    {"number": 5100, "name": "Repairs & Maintenance",     "account_type": "expense",   "is_active": True},
    {"number": 5110, "name": "Supplies",                  "account_type": "expense",   "is_active": True},
    {"number": 5120, "name": "Utilities",                 "account_type": "expense",   "is_active": True},
    {"number": 5130, "name": "Non-Mortgage Interest",     "account_type": "expense",   "is_active": True},
    {"number": 5140, "name": "Advertising",               "account_type": "expense",   "is_active": True},
    {"number": 5150, "name": "Travel & Transportation",   "account_type": "expense",   "is_active": True},
    {"number": 5160, "name": "Professional Services",     "account_type": "expense",   "is_active": True},
    {"number": 5170, "name": "Legal",                     "account_type": "expense",   "is_active": True},
    {"number": 5180, "name": "Insurance",                 "account_type": "expense",   "is_active": True},
    {"number": 5190, "name": "Resort Lot Rental Fees",    "account_type": "expense",   "is_active": True},
    {"number": 5200, "name": "Cleaning Service Fees",     "account_type": "expense",   "is_active": True},
]
# fmt: on


def upgrade() -> None:
    # 1. Create accounts table
    accounts_table = op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("account_type", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("number", name="uq_account_number"),
        sa.UniqueConstraint("name", name="uq_account_name"),
        sa.CheckConstraint(
            "number >= 1000 AND number <= 9999",
            name="ck_account_number_range",
        ),
    )

    # 2. Seed chart of accounts
    op.bulk_insert(accounts_table, CHART_OF_ACCOUNTS)

    # 3. Create journal_entries table
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("source_id", name="uq_journal_entry_source_id"),
    )

    # 4. Create journal_lines table
    op.create_table(
        "journal_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "entry_id",
            sa.Integer(),
            sa.ForeignKey("journal_entries.id"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
    )
    op.create_index("ix_journal_lines_entry_id", "journal_lines", ["entry_id"])
    op.create_index("ix_journal_lines_account_id", "journal_lines", ["account_id"])

    # 5. Create expenses table (stub — ORM model created in plan 03-03)
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column(
            "property_id",
            sa.Integer(),
            sa.ForeignKey("properties.id"),
            nullable=True,
        ),
        sa.Column("attribution", sa.String(32), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("vendor", sa.String(255), nullable=True),
        sa.Column(
            "journal_entry_id",
            sa.Integer(),
            sa.ForeignKey("journal_entries.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # 6. Create loans table (stub — ORM model created in plan 03-04)
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("original_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("interest_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # 7. Create reconciliation_matches table (stub — ORM model created in plan 03-05)
    op.create_table(
        "reconciliation_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "booking_id",
            sa.Integer(),
            sa.ForeignKey("bookings.id"),
            nullable=False,
        ),
        sa.Column(
            "bank_transaction_id",
            sa.Integer(),
            sa.ForeignKey("bank_transactions.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "matched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("confirmed_by", sa.String(128), nullable=True),
        sa.UniqueConstraint("booking_id", name="uq_reconciliation_booking_id"),
        sa.UniqueConstraint(
            "bank_transaction_id", name="uq_reconciliation_bank_transaction_id"
        ),
    )

    # 8. Add reconciliation_status to bookings
    op.add_column(
        "bookings",
        sa.Column(
            "reconciliation_status",
            sa.String(32),
            server_default="unmatched",
            nullable=False,
        ),
    )

    # 9. Add reconciliation_status to bank_transactions
    op.add_column(
        "bank_transactions",
        sa.Column(
            "reconciliation_status",
            sa.String(32),
            server_default="unmatched",
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Reverse order to respect FK constraints
    op.drop_column("bank_transactions", "reconciliation_status")
    op.drop_column("bookings", "reconciliation_status")
    op.drop_table("reconciliation_matches")
    op.drop_table("loans")
    op.drop_table("expenses")
    op.drop_index("ix_journal_lines_account_id", table_name="journal_lines")
    op.drop_index("ix_journal_lines_entry_id", table_name="journal_lines")
    op.drop_table("journal_lines")
    op.drop_table("journal_entries")
    op.drop_table("accounts")
