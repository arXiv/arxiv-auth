"""Authorization scopes for arXiv users and clients."""

EDIT_PROFILE = 'profile:update'
VIEW_PROFILE = 'profile:read'

CREATE_SUBMISSION = 'submission:create'
EDIT_SUBMISSION = 'submission:update'
VIEW_SUBMISSION = 'submission:read'
PROXY_SUBMISSION = 'submission:proxy'

AUTHENTICATED_USER = [
    EDIT_PROFILE,
    VIEW_PROFILE,
    CREATE_SUBMISSION,
    EDIT_SUBMISSION,
    VIEW_SUBMISSION
]
