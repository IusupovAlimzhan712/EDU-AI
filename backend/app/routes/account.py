"""
Account routes - the authenticated user's own profile.

  GET    /api/me                  -> get current profile
  PATCH  /api/me                  -> update profile
  POST   /api/me/change-password  -> change password
  DELETE /api/me                  -> delete account
"""
from flask import Blueprint, request, jsonify

from ..services import AccountService
from ..utils.errors import BadRequestError
from ._decorators import auth_required, current_student_id

account_bp = Blueprint('account', __name__)


def _body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequestError('Request body must be JSON.')
    return data


@account_bp.get('')
@auth_required
def get_me():
    student = AccountService.get_profile(current_student_id())
    return jsonify(student.to_dict()), 200


@account_bp.patch('')
@auth_required
def update_me():
    data = _body()
    student = AccountService.update_profile(
        student_id=current_student_id(),
        full_name=data.get('fullName'),
        form_level=data.get('formLevel'),
    )
    return jsonify({
        'message': 'Profile updated.',
        'student': student.to_dict(),
    }), 200


@account_bp.post('/change-password')
@auth_required
def change_password():
    data = _body()
    AccountService.change_password(
        student_id=current_student_id(),
        current_password=data.get('currentPassword'),
        new_password=data.get('newPassword'),
    )
    return jsonify({
        'message': 'Password changed. Please log in again.',
    }), 200


@account_bp.delete('')
@auth_required
def delete_me():
    AccountService.delete_account(current_student_id())
    return jsonify({'message': 'Account deleted.'}), 200
