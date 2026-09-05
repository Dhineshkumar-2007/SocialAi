"""Notification routes."""
from flask import Blueprint, request, jsonify, session
from auth.decorators import require_role
from models.notification import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.get("")
@require_role("citizen", "admin", "university", "industry")
def list_notifications():
    user = session.get("user")
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    notifications = Notification.list_for_user(user.get("id"), unread_only=unread_only)
    return jsonify({
        "notifications": [n.to_dict() for n in notifications],
        "count": len(notifications),
        "unread_count": len(Notification.list_for_user(user.get("id"), unread_only=True))
    })


@notifications_bp.patch("/<int:notification_id>/read")
@require_role("citizen", "admin", "university", "industry")
def mark_read(notification_id):
    user = session.get("user")
    Notification.mark_read(notification_id, user.get("id"))
    return jsonify({"message": "marked read"})
