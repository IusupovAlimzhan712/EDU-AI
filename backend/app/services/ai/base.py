from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, List


@dataclass
class GeneratedQuestion:
    """A single MCQ question produced by a generator.

    Validators check these before persistence.
    """
    stem: str
    options: List[str]       # must be length 4
    correct_index: int       # 0..3
    explanation: str         # short rationale, shown post-submit
    points: int = 1
    difficulty: str = 'sederhana'  # 'mudah' | 'sederhana' | 'sukar'


class IQuestionGenerator(ABC):
    """Interface every concrete generator must satisfy."""

    @abstractmethod
    def generate_stream(
        self,
        context: str,
        num_questions: int,
        language: str = 'bm',
    ) -> Iterator[GeneratedQuestion]:
        """Yield questions one at a time as they're generated.

        Args:
            context: KSSM-aligned source text the model should ground in.
            num_questions: How many MCQ to produce.
            language: 'bm' for Bahasa Malaysia, 'en' for English.

        Yields:
            GeneratedQuestion instances. Caller is responsible for
            validation + persistence. May yield fewer than requested if
            the model fails repeatedly.
        """
        raise NotImplementedError