r"""MobileNotificationManager — Push notification preferences for mobile SDK.

Manages notification preferences for mobile clients:
    - Register push notification tokens (FCM/APNs)
    - Configure notification types (transfers, staking, governance)
    - Mute/unmute specific notification categories
    - Get notification history

The notification system supports:
    - **FCM** (Firebase Cloud Messaging) for Android
    - **APNs** (Apple Push Notification Service) for iOS
    - **In-app** notifications for both platforms

Notification Types:
    - transfer_received: BAIT received
    - transfer_sent: BAIT sent
    - stake_reward: Staking reward earned
    - governance_proposal: New governance proposal
    - agent_message: Direct message from another agent
    - system_alert: Network maintenance, upgrades

Usage::

    sdk = BaitcoinMobileSDK()
    sdk.notifications.register_push_token('fcm_token_abc', 'android')
    sdk.notifications.set_preference('transfer_received', enabled=True)
"""
import time
import uuid
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class PushToken:
    r"""Registered push notification token."""
    token: str
    platform: str  # 'ios', 'android'
    registered_at: float = field(default_factory=time.time)
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "token": self.token[:8] + "...",
            "platform": self.platform,
            "registered_at": self.registered_at,
            "is_active": self.is_active,
        }


class MobileNotificationManager:
    r"""Mobile push notification management."""

    NOTIFICATION_TYPES = [
        "transfer_received",
        "transfer_sent",
        "stake_reward",
        "governance_proposal",
        "agent_message",
        "system_alert",
    ]

    def __init__(self, sdk: 'BaitcoinMobileSDK'):
        self._sdk = sdk
        self._push_tokens: List[PushToken] = []
        self._preferences: Dict[str, bool] = {
            t: True for t in self.NOTIFICATION_TYPES
        }
        self._history: List[dict] = []

    def register_push_token(self, token: str, platform: str) -> dict:
        r"""Register a push notification token.

        Parameters
        ----------
        token : str
            FCM or APNs device token
        platform : str
            'ios' or 'android'
        """
        # Deactivate old tokens for same platform
        for pt in self._push_tokens:
            if pt.platform == platform:
                pt.is_active = False

        push_token = PushToken(token=token, platform=platform)
        self._push_tokens.append(push_token)

        return {
            "success": True,
            "platform": platform,
            "active_tokens": sum(1 for t in self._push_tokens if t.is_active),
        }

    def unregister_push_token(self, token: str) -> dict:
        r"""Unregister a push notification token."""
        for pt in self._push_tokens:
            if pt.token == token:
                pt.is_active = False
                return {"success": True}
        return {"error": "token_not_found"}

    def set_preference(self, notification_type: str, enabled: bool) -> dict:
        r"""Enable or disable a notification type.

        Parameters
        ----------
        notification_type : str
            One of NOTIFICATION_TYPES
        enabled : bool
            Whether to send this notification type
        """
        if notification_type not in self.NOTIFICATION_TYPES:
            return {"error": "unknown_type", "valid_types": self.NOTIFICATION_TYPES}

        self._preferences[notification_type] = enabled
        return {
            "success": True,
            "notification_type": notification_type,
            "enabled": enabled,
        }

    def get_preferences(self) -> dict:
        r"""Get all notification preferences."""
        return dict(self._preferences)

    def get_notification_history(
        self,
        limit: int = 50,
        offset: int = 0,
        notification_type: str = None,
    ) -> dict:
        r"""Get notification history with pagination."""
        history = self._history
        if notification_type:
            history = [
                n for n in history if n.get("type") == notification_type
            ]

        total = len(history)
        page = history[offset:offset + limit]

        return {
            "notifications": page,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def add_notification(self, notification_type: str, title: str,
                          body: str, data: dict = None) -> dict:
        r"""Add a notification to history (called by SDK internally)."""
        notification = {
            "id": uuid.uuid4().hex[:12],
            "type": notification_type,
            "title": title,
            "body": body,
            "data": data or {},
            "timestamp": time.time(),
            "read": False,
        }
        self._history.append(notification)

        # Keep max 1000 notifications
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        return notification

    def mark_read(self, notification_id: str) -> dict:
        r"""Mark a notification as read."""
        for n in self._history:
            if n.get("id") == notification_id:
                n["read"] = True
                return {"success": True}
        return {"error": "notification_not_found"}

    def mark_all_read(self) -> dict:
        r"""Mark all notifications as read."""
        count = 0
        for n in self._history:
            if not n.get("read", False):
                n["read"] = True
                count += 1
        return {"success": True, "marked_read": count}

    def get_unread_count(self) -> int:
        r"""Count unread notifications."""
        return sum(1 for n in self._history if not n.get("read", False))

    def to_dict(self) -> dict:
        r"""Full notification state export."""
        return {
            "push_tokens": [t.to_dict() for t in self._push_tokens],
            "preferences": self._preferences,
            "unread_count": self.get_unread_count(),
            "total_notifications": len(self._history),
        }
