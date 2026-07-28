from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt,
)

from ..services import AccountService
from ._utils import _body

auth_bp = Blueprint('auth', __name__)



# Registration


@auth_bp.post('/register')
def register():
    data = _body()
    student, tokens = AccountService.register(
        email=data.get('email'),
        password=data.get('password'),
        full_name=data.get('fullName'),
        form_level=data.get('formLevel'),
    )
    return jsonify({
        'message': 'Registration successful.',
        'student': student.to_dict(),
        **tokens,
    }), 201



# Login / Logout / Refresh


@auth_bp.post('/login')
def login():
    data = _body()
    student, tokens = AccountService.login(
        email=data.get('email'),
        password=data.get('password'),
    )
    return jsonify({
        'message': 'Login successful.',
        'student': student.to_dict(),
        **tokens,
    }), 200


@auth_bp.post('/logout')
@jwt_required()
def logout():
    jti = get_jwt().get('jti')
    AccountService.logout(jti)
    return jsonify({'message': 'Logged out.'}), 200


@auth_bp.post('/refresh')
@jwt_required(refresh=True)
def refresh():
    student_id = int(get_jwt_identity())
    payload = AccountService.refresh_token(student_id)
    return jsonify(payload), 200


# ---------------------------------------------------------------------------
# Password reset (UC 4.3.4)
# ---------------------------------------------------------------------------

@auth_bp.post('/forgot-password')
def forgot_password():
    data = _body()
    raw_token = AccountService.request_password_reset(email=data.get('email'))

    response = {
        'message': (
            'If an account with that email exists, a password reset link has been sent.'
        ),
    }
    # In dev mode, surface the token directly so you can test the flow
    # without configuring SMTP. This is gated by DEV_RETURN_RESET_TOKEN.
    if raw_token and current_app.config.get('DEV_RETURN_RESET_TOKEN'):
        response['devResetToken'] = raw_token
    return jsonify(response), 200


@auth_bp.post('/reset-password')
def reset_password():
    data = _body()
    AccountService.reset_password(
        token=data.get('token'),
        new_password=data.get('newPassword'),
    )
    return jsonify({'message': 'Password reset successful. Please log in.'}), 200
