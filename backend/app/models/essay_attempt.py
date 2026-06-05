"""
EssayAttempt — one student's attempt at one EssayQuestion.

grading_status lifecycle:
  'pending'  → attempt created, not yet submitted
  'grading'  → SSE stream in progress
  'done'     → feedback stored, score assigned
  'failed'   → LLM grading hit an unrecoverable error

is_note_form: set only for 'esei' type questions; null for 'struktur'.
  When True, aras_level is clamped to ≤2 and score to ≤4 in backend code
  regardless of what the LLM returns.

matched_codes_json (struktur only): list of matched node results preserving
  F/H/C hierarchy, including evidence quotes. Null for esei.

feedback_json: stored as-is from LLM response (validated before storage).
  For esei: includes arasDescriptorScores and arasReasoning.
"""
from datetime import datetime

from ..extensions import db


class EssayAttempt(db.Model):
    __tablename__ = 'essay_attempt'

    attempt_id = db.Column(
        'attemptId', db.Integer, primary_key=True, autoincrement=True
    )
    student_id = db.Column(
        'studentId',
        db.Integer,
        db.ForeignKey('student.studentId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    question_id = db.Column(
        'questionId',
        db.Integer,
        db.ForeignKey('essay_question.questionId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    response_text = db.Column('responseText', db.Text, nullable=True)
    status = db.Column(db.String(16), nullable=False, default='draft')
    grading_status = db.Column(
        'gradingStatus', db.String(16), nullable=False, default='pending'
    )
    is_note_form = db.Column('isNoteForm', db.Boolean, nullable=True)
    aras_level = db.Column('arasLevel', db.Integer, nullable=True)
    score = db.Column(db.Float, nullable=True)
    max_score = db.Column('maxScore', db.Integer, nullable=True)
    matched_codes_json = db.Column('matchedCodesJson', db.JSON, nullable=True)
    feedback_json = db.Column('feedbackJson', db.JSON, nullable=True)
    started_at = db.Column(
        'startedAt', db.DateTime, nullable=False, default=datetime.utcnow
    )
    submitted_at = db.Column('submittedAt', db.DateTime, nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('draft', 'submitted', 'graded')", name='ck_ea_status'
        ),
        db.CheckConstraint(
            "gradingStatus IN ('pending', 'grading', 'done', 'failed')",
            name='ck_ea_grading_status',
        ),
    )

    question = db.relationship('EssayQuestion', back_populates='attempts')
    student = db.relationship('Student')

    def to_summary_dict(self) -> dict:
        percentage = None
        if self.max_score and self.max_score > 0 and self.score is not None:
            percentage = round((self.score / self.max_score) * 100, 1)
        return {
            'attemptId': self.attempt_id,
            'questionId': self.question_id,
            'studentId': self.student_id,
            'status': self.status,
            'gradingStatus': self.grading_status,
            'isNoteForm': self.is_note_form,
            'arasLevel': self.aras_level,
            'score': self.score,
            'maxScore': self.max_score,
            'percentage': percentage,
            'startedAt': self.started_at.isoformat() if self.started_at else None,
            'submittedAt': self.submitted_at.isoformat() if self.submitted_at else None,
        }

    def to_dict(self) -> dict:
        d = self.to_summary_dict()
        d['responseText'] = self.response_text
        d['matchedNodes'] = self.matched_codes_json
        d['feedbackJson'] = self.feedback_json
        return d
