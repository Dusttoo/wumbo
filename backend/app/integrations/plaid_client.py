"""Plaid API client integration"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import plaid
from app.core.config import settings
from app.core.logging import logger
from plaid.api import plaid_api
from plaid.api_client import ApiClient
from plaid.configuration import Configuration
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.item_public_token_exchange_request import \
    ItemPublicTokenExchangeRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import \
    LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest


class PlaidClient:
    """Plaid API client wrapper"""

    def __init__(self):
        """Initialize Plaid client"""
        # Configure Plaid client
        configuration = Configuration(
            host=self._get_plaid_host(),
            api_key={
                "clientId": settings.PLAID_CLIENT_ID,
                "secret": settings.PLAID_SECRET,
            },
        )

        api_client = ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

    def _get_plaid_host(self) -> str:
        """Get Plaid API host based on environment"""
        env_map = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Development,
            "production": plaid.Environment.Production,
        }
        return env_map.get(settings.PLAID_ENVIRONMENT.lower(), plaid.Environment.Sandbox)

    def create_link_token(
        self,
        user_id: str,
        client_name: str = "Wumbo",
        products: Optional[List[str]] = None,
        webhook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a link token for Plaid Link initialization

        Args:
            user_id: Unique user identifier
            client_name: Name displayed in Plaid Link
            products: List of Plaid products to use
            webhook: Webhook URL for notifications

        Returns:
            dict with link_token and expiration
        """
        if products is None:
            products = [Products("transactions")]
        else:
            products = [Products(p) for p in products]

        try:
            request = LinkTokenCreateRequest(
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                client_name=client_name,
                products=products,
                country_codes=[CountryCode("US")],
                language="en",
                webhook=webhook,
            )

            response = self.client.link_token_create(request)
            result = response.to_dict()

            logger.info(f"Created link token for user {user_id}")
            return {
                "link_token": result["link_token"],
                "expiration": result["expiration"],
            }

        except plaid.ApiException as e:
            logger.error(f"Plaid API error creating link token: {e}")
            raise

    def exchange_public_token(self, public_token: str) -> Dict[str, str]:
        """
        Exchange public token for access token

        Args:
            public_token: Public token from Plaid Link

        Returns:
            dict with access_token and item_id
        """
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            result = response.to_dict()

            logger.info(f"Exchanged public token for item {result['item_id']}")
            return {
                "access_token": result["access_token"],
                "item_id": result["item_id"],
            }

        except plaid.ApiException as e:
            logger.error(f"Plaid API error exchanging token: {e}")
            raise

    def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Get accounts for an access token

        Args:
            access_token: Plaid access token

        Returns:
            List of account dictionaries
        """
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            result = response.to_dict()

            accounts = result.get("accounts", [])
            logger.info(f"Retrieved {len(accounts)} accounts")
            return accounts

        except plaid.ApiException as e:
            logger.error(f"Plaid API error getting accounts: {e}")
            raise

    def get_item(self, access_token: str) -> Dict[str, Any]:
        """
        Get item information

        Args:
            access_token: Plaid access token

        Returns:
            Item information dictionary
        """
        try:
            request = ItemGetRequest(access_token=access_token)
            response = self.client.item_get(request)
            result = response.to_dict()

            logger.info(f"Retrieved item info for {result['item']['item_id']}")
            return result["item"]

        except plaid.ApiException as e:
            logger.error(f"Plaid API error getting item: {e}")
            raise

    def sync_transactions(
        self, access_token: str, cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync transactions using Transactions Sync endpoint

        Args:
            access_token: Plaid access token
            cursor: Cursor for pagination

        Returns:
            dict with added, modified, removed transactions and next cursor
        """
        try:
            request = TransactionsSyncRequest(access_token=access_token, cursor=cursor)
            response = self.client.transactions_sync(request)
            result = response.to_dict()

            added = result.get("added", [])
            modified = result.get("modified", [])
            removed = result.get("removed", [])
            has_more = result.get("has_more", False)
            next_cursor = result.get("next_cursor")

            logger.info(
                f"Synced transactions: {len(added)} added, "
                f"{len(modified)} modified, {len(removed)} removed"
            )

            return {
                "added": added,
                "modified": modified,
                "removed": removed,
                "has_more": has_more,
                "next_cursor": next_cursor,
            }

        except plaid.ApiException as e:
            logger.error(f"Plaid API error syncing transactions: {e}")
            raise

    def get_transactions(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
        account_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for a date range (fallback method)

        Args:
            access_token: Plaid access token
            start_date: Start date for transactions
            end_date: End date for transactions
            account_ids: Optional list of account IDs to filter

        Returns:
            List of transaction dictionaries
        """
        try:
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date.date(),
                end_date=end_date.date(),
                options={"account_ids": account_ids} if account_ids else None,
            )

            response = self.client.transactions_get(request)
            result = response.to_dict()

            transactions = result.get("transactions", [])
            logger.info(f"Retrieved {len(transactions)} transactions")
            return transactions

        except plaid.ApiException as e:
            logger.error(f"Plaid API error getting transactions: {e}")
            raise

    def remove_item(self, access_token: str) -> bool:
        """
        Remove (unlink) a Plaid item

        Args:
            access_token: Plaid access token

        Returns:
            True if successful
        """
        try:
            request = ItemRemoveRequest(access_token=access_token)
            self.client.item_remove(request)

            logger.info("Successfully removed Plaid item")
            return True

        except plaid.ApiException as e:
            logger.error(f"Plaid API error removing item: {e}")
            raise


# Global Plaid client instance
plaid_client = PlaidClient()
