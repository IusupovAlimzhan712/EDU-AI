"""
Services / Control classes (Business Logic layer).

Each service maps directly to a Control class from Table 4.28 of the FYP1
report:

    AccountService  -> AccountManager
    TopicService    -> TopicManager

(Phase 3 will add: RoutingAgent, KnowledgeAgent, AssessmentAgent,
ContentValidator. QuizService is Phase 2 weeks 5-6.)
"""
from .account_service import AccountService
from .topic_service import TopicService

__all__ = ['AccountService', 'TopicService']
