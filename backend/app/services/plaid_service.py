"""Plaid service for business logic"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.integrations.plaid_client import plaid_client
from app.models.bank_account import BankAccount
from app.models.transaction import Transaction
from app.models.user import User
from sqlalchemy.orm import Session


class PlaidService:
    """Service for Plaid-related operations"""

    @staticmethod
    def create_link_token(db: Session, user: User, webhook: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Plaid Link token for a user

        Args:
            db: Database session
            user: User to create token for
            webhook: Optional webhook URL

        Returns:
            dict with link_token and expiration
        """
        return plaid_client.create_link_token(
            user_id=str(user.id),
            client_name="Wumbo",
            products=["transactions"],
            webhook=webhook,
        )

    @staticmethod
    def exchange_public_token_and_save_accounts(
        db: Session, user: User, household_id: str, public_token: str
    ) -> int:
        """
        Exchange public token and save connected accounts

        Args:
            db: Database session
            user: User who connected the account
            household_id: Household ID
            public_token: Public token from Plaid Link

        Returns:
            Number of accounts added
        """
        # Exchange token
        exchange_result = plaid_client.exchange_public_token(public_token)
        access_token = exchange_result["access_token"]
        item_id = exchange_result["item_id"]

        # Get accounts
        accounts = plaid_client.get_accounts(access_token)

        # Save accounts to database
        accounts_added = 0
        for account_data in accounts:
            # Check if account already exists
            existing = (
                db.query(BankAccount)
                .filter(BankAccount.plaid_account_id == account_data["account_id"])
                .first()
            )

            if existing:
                logger.warning(f"Account {account_data['account_id']} already exists, skipping")
                continue

            # Get balance info
            balances = account_data.get("balances", {})

            # Create new account
            account = BankAccount(
                household_id=household_id,
                user_id=user.id,
                plaid_account_id=account_data["account_id"],
                plaid_item_id=item_id,
                plaid_access_token=access_token,  # Automatically encrypted by EncryptedString column type
                name=account_data.get("name", "Unknown Account"),
                official_name=account_data.get("official_name"),
                mask=account_data.get("mask"),
                account_type=account_data.get("type"),
                account_subtype=account_data.get("subtype"),
                current_balance=balances.get("current"),
                available_balance=balances.get("available"),
                currency_code=balances.get("iso_currency_code", "USD"),
            )

            db.add(account)
            accounts_added += 1

        db.commit()
        logger.info(f"Added {accounts_added} bank accounts for user {user.id}")
        return accounts_added

    @staticmethod
    def sync_account_transactions(db: Session, account_id: str) -> Dict[str, int]:
        """
        Sync transactions for a specific account

        Args:
            db: Database session
            account_id: Bank account ID (UUID)

        Returns:
            dict with counts of added, modified, removed transactions
        """
        # Get account
        account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")

        # Sync transactions
        cursor = account.plaid_cursor
        sync_result = plaid_client.sync_transactions(account.plaid_access_token, cursor)

        added_count = 0
        modified_count = 0
        removed_count = 0

        # Process added transactions
        for txn_data in sync_result["added"]:
            PlaidService._save_transaction(db, account, txn_data)
            added_count += 1

        # Process modified transactions
        for txn_data in sync_result["modified"]:
            PlaidService._update_transaction(db, txn_data)
            modified_count += 1

        # Process removed transactions
        for txn_data in sync_result["removed"]:
            PlaidService._remove_transaction(db, txn_data["transaction_id"])
            removed_count += 1

        # Update cursor and last synced
        account.plaid_cursor = sync_result["next_cursor"]
        account.last_synced_at = datetime.utcnow()
        account.sync_error = None

        db.commit()

        logger.info(
            f"Synced account {account_id}: {added_count} added, "
            f"{modified_count} modified, {removed_count} removed"
        )

        return {
            "added": added_count,
            "modified": modified_count,
            "removed": removed_count,
        }

    @staticmethod
    def _save_transaction(db: Session, account: BankAccount, txn_data: Dict[str, Any]) -> None:
        """Save a new transaction"""
        # Check if transaction already exists
        existing = (
            db.query(Transaction)
            .filter(Transaction.plaid_transaction_id == txn_data["transaction_id"])
            .first()
        )

        if existing:
            logger.warning(f"Transaction {txn_data['transaction_id']} already exists, updating")
            PlaidService._update_transaction(db, txn_data)
            return

        # Create new transaction
        transaction = Transaction(
            account_id=account.id,
            household_id=account.household_id,
            plaid_transaction_id=txn_data["transaction_id"],
            amount=abs(txn_data["amount"]),  # Plaid uses negative for expenses
            date=datetime.strptime(txn_data["date"], "%Y-%m-%d").date(),
            authorized_date=(
                datetime.strptime(txn_data["authorized_date"], "%Y-%m-%d").date()
                if txn_data.get("authorized_date")
                else None
            ),
            name=txn_data["name"],
            merchant_name=txn_data.get("merchant_name"),
            plaid_category=", ".join(txn_data.get("category", [])),
            plaid_category_id=txn_data.get("category_id"),
            payment_channel=txn_data.get("payment_channel"),
            pending=txn_data.get("pending", False),
            is_manual=False,
        )

        db.add(transaction)

    @staticmethod
    def _update_transaction(db: Session, txn_data: Dict[str, Any]) -> None:
        """Update an existing transaction"""
        transaction = (
            db.query(Transaction)
            .filter(Transaction.plaid_transaction_id == txn_data["transaction_id"])
            .first()
        )

        if not transaction:
            logger.warning(f"Transaction {txn_data['transaction_id']} not found for update")
            return

        # Update fields
        transaction.amount = abs(txn_data["amount"])
        transaction.date = datetime.strptime(txn_data["date"], "%Y-%m-%d").date()
        transaction.name = txn_data["name"]
        transaction.merchant_name = txn_data.get("merchant_name")
        transaction.pending = txn_data.get("pending", False)
        transaction.plaid_category = ", ".join(txn_data.get("category", []))
        transaction.plaid_category_id = txn_data.get("category_id")
        transaction.payment_channel = txn_data.get("payment_channel")

    @staticmethod
    def _remove_transaction(db: Session, plaid_transaction_id: str) -> None:
        """Remove a transaction"""
        transaction = (
            db.query(Transaction)
            .filter(Transaction.plaid_transaction_id == plaid_transaction_id)
            .first()
        )

        if transaction:
            db.delete(transaction)
            logger.info(f"Removed transaction {plaid_transaction_id}")

    @staticmethod
    def remove_account(db: Session, account_id: str) -> bool:
        """
        Remove a bank account and unlink from Plaid

        Args:
            db: Database session
            account_id: Bank account ID

        Returns:
            True if successful
        """
        account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")

        # Remove from Plaid
        plaid_client.remove_item(account.plaid_access_token)

        # Delete from database (cascade will delete transactions)
        db.delete(account)
        db.commit()

        logger.info(f"Removed account {account_id}")
        return True
