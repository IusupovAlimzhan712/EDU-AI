"""
HTTP routes (Presentation/Boundary layer).

These are thin: they parse JSON, call a service, and serialize the result.
Business logic lives in services/, never in routes/.
"""
