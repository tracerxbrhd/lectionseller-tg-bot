"""Initial schema.

Revision ID: 20260524_0001
Revises:
Create Date: 2026-05-24 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260524_0001"
down_revision = None
branch_labels = None
depends_on = None


content_type_enum = postgresql.ENUM(
    "pdf",
    "video",
    "audio",
    "image",
    "text",
    name="content_type",
    create_type=False,
)
purchase_type_enum = postgresql.ENUM(
    "lecture",
    "block",
    "section",
    name="purchase_type",
    create_type=False,
)
purchase_status_enum = postgresql.ENUM(
    "pending",
    "paid",
    "canceled",
    "refunded",
    name="purchase_status",
    create_type=False,
)
payment_provider_enum = postgresql.ENUM(
    "yookassa",
    name="payment_provider",
    create_type=False,
)
payment_status_enum = postgresql.ENUM(
    "pending",
    "succeeded",
    "canceled",
    "waiting_for_capture",
    "failed",
    name="payment_status",
    create_type=False,
)
support_request_status_enum = postgresql.ENUM(
    "open",
    "in_progress",
    "closed",
    name="support_request_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    content_type_enum.create(bind, checkfirst=True)
    purchase_type_enum.create(bind, checkfirst=True)
    purchase_status_enum.create(bind, checkfirst=True)
    payment_provider_enum.create(bind, checkfirst=True)
    payment_status_enum.create(bind, checkfirst=True)
    support_request_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "admin_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_admin_accounts"),
        sa.UniqueConstraint("username", name="uq_admin_accounts_username"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=False)

    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sections"),
    )

    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_blocks_price_non_negative"),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_blocks_section_id_sections",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_blocks"),
    )
    op.create_index("ix_blocks_section_id", "blocks", ["section_id"], unique=False)

    op.create_table(
        "lectures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("full_description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_lectures_price_non_negative"),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["blocks.id"],
            name="fk_lectures_block_id_blocks",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lectures"),
    )
    op.create_index("ix_lectures_block_id", "lectures", ["block_id"], unique=False)

    op.create_table(
        "content_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lecture_id", sa.Integer(), nullable=False),
        sa.Column("type", content_type_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("telegram_file_id", sa.String(length=512), nullable=True),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("protected_content_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint(
            "(type = 'text' AND text_content IS NOT NULL) OR "
            "(type <> 'text' AND (file_path IS NOT NULL OR telegram_file_id IS NOT NULL))",
            name="ck_content_items_content_source_present",
        ),
        sa.ForeignKeyConstraint(
            ["lecture_id"],
            ["lectures.id"],
            name="fk_content_items_lecture_id_lectures",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_content_items"),
    )
    op.create_index("ix_content_items_lecture_id", "content_items", ["lecture_id"], unique=False)

    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purchase_type", purchase_type_enum, nullable=False),
        sa.Column("object_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", purchase_status_enum, server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("price >= 0", name="ck_purchases_price_non_negative"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_purchases_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchases"),
    )
    op.create_index("ix_purchases_object_id", "purchases", ["object_id"], unique=False)
    op.create_index("ix_purchases_purchase_type", "purchases", ["purchase_type"], unique=False)
    op.create_index("ix_purchases_status", "purchases", ["status"], unique=False)
    op.create_index("ix_purchases_user_id", "purchases", ["user_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.Integer(), nullable=False),
        sa.Column("provider", payment_provider_enum, nullable=False),
        sa.Column("provider_payment_id", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", payment_status_enum, server_default="pending", nullable=False),
        sa.Column("confirmation_url", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount_non_negative"),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
            name="fk_payments_purchase_id_purchases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_payments_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        sa.UniqueConstraint("provider_payment_id", name="uq_payments_provider_payment_id"),
        sa.UniqueConstraint("purchase_id", name="uq_payments_purchase_id"),
    )
    op.create_index("ix_payments_status", "payments", ["status"], unique=False)
    op.create_index("ix_payments_user_id", "payments", ["user_id"], unique=False)

    op.create_table(
        "access_grants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lecture_id", sa.Integer(), nullable=False),
        sa.Column("source_purchase_id", sa.Integer(), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(
            ["granted_by_admin_id"],
            ["admin_accounts.id"],
            name="fk_access_grants_granted_by_admin_id_admin_accounts",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["lecture_id"],
            ["lectures.id"],
            name="fk_access_grants_lecture_id_lectures",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_purchase_id"],
            ["purchases.id"],
            name="fk_access_grants_source_purchase_id_purchases",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_access_grants_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_access_grants"),
        sa.UniqueConstraint(
            "source_purchase_id",
            "lecture_id",
            "user_id",
            name="uq_access_grants_purchase_lecture_user",
        ),
    )
    op.create_index("ix_access_grants_lecture_id", "access_grants", ["lecture_id"], unique=False)
    op.create_index("ix_access_grants_user_id", "access_grants", ["user_id"], unique=False)

    op.create_table(
        "support_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", support_request_status_enum, server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_support_requests_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_support_requests"),
    )
    op.create_index("ix_support_requests_status", "support_requests", ["status"], unique=False)
    op.create_index("ix_support_requests_user_id", "support_requests", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_support_requests_user_id", table_name="support_requests")
    op.drop_index("ix_support_requests_status", table_name="support_requests")
    op.drop_table("support_requests")

    op.drop_index("ix_access_grants_user_id", table_name="access_grants")
    op.drop_index("ix_access_grants_lecture_id", table_name="access_grants")
    op.drop_table("access_grants")

    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_purchases_user_id", table_name="purchases")
    op.drop_index("ix_purchases_status", table_name="purchases")
    op.drop_index("ix_purchases_purchase_type", table_name="purchases")
    op.drop_index("ix_purchases_object_id", table_name="purchases")
    op.drop_table("purchases")

    op.drop_index("ix_content_items_lecture_id", table_name="content_items")
    op.drop_table("content_items")

    op.drop_index("ix_lectures_block_id", table_name="lectures")
    op.drop_table("lectures")

    op.drop_index("ix_blocks_section_id", table_name="blocks")
    op.drop_table("blocks")

    op.drop_table("sections")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.drop_table("admin_accounts")

    bind = op.get_bind()
    support_request_status_enum.drop(bind, checkfirst=True)
    payment_status_enum.drop(bind, checkfirst=True)
    payment_provider_enum.drop(bind, checkfirst=True)
    purchase_status_enum.drop(bind, checkfirst=True)
    purchase_type_enum.drop(bind, checkfirst=True)
    content_type_enum.drop(bind, checkfirst=True)

