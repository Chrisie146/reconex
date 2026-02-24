"""
Authentication routes: register, login, profile, change password,
forgot password and reset password.
"""

import re
from collections import defaultdict
from time import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    create_password_reset_token,
    get_current_user,
    get_password_hash,
    verify_password,
    verify_password_reset_token,
)
import resend

from config import ENVIRONMENT, FRONTEND_URL, Config
from exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    RateLimitError,
    ValidationError,
)
from models import Client, User, get_db
from routers.dependencies import logger
from schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

# ---------------------------------------------------------------------------
# In-memory rate limiter for password reset requests
# Key: client IP, Value: list of UNIX timestamps for requests in current window
# NOTE: For multi-worker / multi-server deployments, replace with a Redis-backed
#       rate limiter so state is shared across all processes.
# ---------------------------------------------------------------------------
_RESET_WINDOW_SECONDS = 900   # 15-minute sliding window
_RESET_MAX_REQUESTS = 3       # max 3 attempts per IP per window
_reset_tracker: dict = defaultdict(list)


def _is_rate_limited(ip: str) -> bool:
    """Return True when the caller has exceeded the reset-request limit."""
    now = time()
    cutoff = now - _RESET_WINDOW_SECONDS
    _reset_tracker[ip] = [t for t in _reset_tracker[ip] if t > cutoff]
    if len(_reset_tracker[ip]) >= _RESET_MAX_REQUESTS:
        return True
    _reset_tracker[ip].append(now)
    return False


# ---------------------------------------------------------------------------
# Password-strength validation
# ---------------------------------------------------------------------------
def _validate_password_strength(password: str) -> None:
    """Raise ValidationError if password does not meet strength requirements."""
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("a lowercase letter")
    if not re.search(r"\d", password):
        errors.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("a special character (!@#$%^&* etc.)")
    if errors:
        raise ValidationError(f"Password must contain: {', '.join(errors)}")


# ---------------------------------------------------------------------------
# Email helper — Resend
# ---------------------------------------------------------------------------
def _build_reset_email_html(reset_link: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reset Your Password</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;border:1px solid #e4e4e7;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background-color:#2563eb;padding:32px 40px;text-align:center;">
              <span style="font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">StatementBur</span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">
              <h1 style="margin:0 0 16px;font-size:20px;font-weight:600;color:#18181b;">Reset your password</h1>
              <p style="margin:0 0 24px;font-size:15px;color:#52525b;line-height:1.6;">
                We received a request to reset the password for your StatementBur account.
                Click the button below to choose a new password.
              </p>

              <!-- Button -->
              <table cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
                <tr>
                  <td style="background-color:#2563eb;border-radius:6px;">
                    <a href="{reset_link}"
                       style="display:inline-block;padding:12px 28px;font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;">
                      Reset My Password
                    </a>
                  </td>
                </tr>
              </table>

              <p style="margin:0 0 8px;font-size:13px;color:#71717a;line-height:1.6;">
                This link expires in <strong>15 minutes</strong>.
                If you did not request a password reset, you can safely ignore this email — your password will not change.
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr style="border:none;border-top:1px solid #e4e4e7;margin:0;" />
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px;text-align:center;">
              <p style="margin:0;font-size:12px;color:#a1a1aa;">
                &copy; 2025 StatementBur. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _send_reset_email(to_email: str, reset_link: str) -> None:
    """Send a password-reset email via Resend. Fire-and-forget — never raises."""
    api_key = Config.RESEND_API_KEY
    if not api_key:
        logger.warning("[EMAIL] RESEND_API_KEY not set — skipping email send")
        return

    try:
        resend.api_key = api_key
        resend.Emails.send({
            "from": Config.FROM_EMAIL,
            "to": [to_email],
            "subject": "Reset your StatementBur password",
            "html": _build_reset_email_html(reset_link),
        })
        logger.info(f"[EMAIL] Password reset email sent to {to_email}")
    except Exception as exc:
        logger.error(f"[EMAIL] Failed to send reset email to {to_email}: {exc}")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
def register(request: UserRegister, db: Session = Depends(get_db)):
    """Register a new user (accountant)"""
    try:
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise ConflictError("Email already registered")

        if len(request.password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        hashed_password = get_password_hash(request.password)
        new_user = User(
            email=request.email,
            hashed_password=hashed_password,
            full_name=request.full_name or request.email.split("@")[0],
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        default_client = Client(user_id=new_user.id, name="My Business")
        db.add(default_client)
        db.commit()
        db.refresh(default_client)

        access_token = create_access_token(data={"sub": str(new_user.id)})

        logger.info(f"New user registered: {request.email} with default client")

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
        )

    except (ValidationError, ConflictError):
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise DatabaseError("Failed to register user")


@router.post("/login", response_model=TokenResponse)
def login(request: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password"""
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user or not verify_password(request.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthorizationError("User account is disabled")

        access_token = create_access_token(data={"sub": str(user.id)})
        logger.info(f"User logged in: {request.email}")

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
        )

    except (AuthenticationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise DatabaseError("Failed to login")


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's profile"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change current user's password"""
    try:
        if not verify_password(request.old_password, current_user.hashed_password):
            raise AuthenticationError("Old password is incorrect")

        if len(request.new_password) < 8:
            raise ValidationError("New password must be at least 8 characters")

        if request.new_password != request.new_password_confirm:
            raise ValidationError("Passwords do not match")

        current_user.hashed_password = get_password_hash(request.new_password)
        db.commit()

        logger.info(f"Password changed for user: {current_user.email}")
        return {"success": True, "message": "Password changed successfully"}

    except (AuthenticationError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise DatabaseError("Failed to change password")


# ---------------------------------------------------------------------------
# Forgot password
# ---------------------------------------------------------------------------

_GENERIC_RESET_RESPONSE = {
    "success": True,
    "message": (
        "If that email address is registered you will receive "
        "password reset instructions shortly."
    ),
}


@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    req: Request,
    db: Session = Depends(get_db),
):
    """
    Request a password-reset link.

    Always returns the same generic response to prevent account enumeration.
    Rate-limited to 3 requests per IP per 15-minute window.
    """
    client_ip = req.client.host if req.client else "unknown"

    if _is_rate_limited(client_ip):
        logger.warning(
            f"Password reset rate limit exceeded for IP {client_ip}"
        )
        raise RateLimitError(
            "Too many password reset requests. Please wait 15 minutes before trying again.",
            retry_after=_RESET_WINDOW_SECONDS,
        )

    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        # Don't reveal whether the email exists
        logger.info(f"Password reset requested for unknown email: {request.email}")
        return _GENERIC_RESET_RESPONSE

    token = create_password_reset_token(user.email, user.hashed_password)
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"

    if ENVIRONMENT != "production":
        # Always print the link in dev so it's easy to test without email
        logger.info(f"[DEV] Password reset link for {user.email}: {reset_link}")
        print(f"\n{'='*60}\nPassword Reset Link (dev only):\n{reset_link}\n{'='*60}\n", flush=True)

    _send_reset_email(user.email, reset_link)

    return _GENERIC_RESET_RESPONSE


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------

@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Reset a user's password using a valid reset token.

    Token single-use is enforced statelessly: the token embeds a hint of the
    user's current password hash.  Once the password is updated the hint no
    longer matches, making the old token permanently invalid.
    """
    # 1. Decode & validate the JWT structure / expiry / purpose
    payload = verify_password_reset_token(request.token)
    if not payload:
        logger.warning("Invalid or expired password reset token presented")
        raise AuthenticationError("Invalid or expired reset link. Please request a new one.")

    email: str = payload["sub"]
    hint: str = payload.get("hint", "")

    # 2. Fetch the user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise AuthenticationError("Invalid or expired reset link. Please request a new one.")

    # 3. Check the token hasn't already been used (password hash changed ⟹ hint mismatch)
    if user.hashed_password[:16] != hint:
        logger.warning(f"Attempted reuse of consumed password reset token for {email}")
        raise AuthenticationError(
            "This reset link has already been used. Please request a new one."
        )

    # 4. Validate new-password strength
    _validate_password_strength(request.new_password)

    if request.new_password != request.new_password_confirm:
        raise ValidationError("Passwords do not match")

    # 5. Persist the new password
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    logger.info(f"Password successfully reset for: {email}")
    return {"success": True, "message": "Password reset successfully. You can now log in with your new password."}
