from ..extensions import db


class TopicChunk(db.Model):
    __tablename__ = 'topic_chunk'

    chunk_id = db.Column(
        'chunkId', db.Integer, primary_key=True, autoincrement=True
    )
    topic_id = db.Column(
        'topicId',
        db.Integer,
        db.ForeignKey('topic.topicId', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    page_number = db.Column('pageNumber', db.Integer, nullable=False)
    chunk_index = db.Column('chunkIndex', db.Integer, nullable=False)
    text_content = db.Column('textContent', db.Text, nullable=False, default='')
    word_count = db.Column('wordCount', db.Integer, nullable=False, default=0)
    # float32 bytes: 1536 dims × 4 bytes = 6144 bytes per chunk
    embedding = db.Column('embedding', db.LargeBinary, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('topicId', 'pageNumber', 'chunkIndex', name='uq_topic_chunk'),
        db.CheckConstraint('pageNumber >= 1', name='ck_chunk_page_positive'),
    )

    topic = db.relationship('Topic', backref=db.backref('chunks', lazy='dynamic'))

    def __repr__(self) -> str:
        return (
            f'<TopicChunk topic={self.topic_id} '
            f'page={self.page_number} idx={self.chunk_index}>'
        )
