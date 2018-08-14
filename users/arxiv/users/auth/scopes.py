"""
Authorization scopes for arXiv users and clients.

The concept of authorization scope comes from OAuth 2.0 (`RFC 6749 §3.3
<https://tools.ietf.org/html/rfc6749#section-3.3>`_). For a nice primer, see
`this blog post <https://brandur.org/oauth-scope>`_. The basic idea is that
the authorization associated with an access token can be limited, e.g. to
limit what actions an API client can take on behalf of a user.

In this package, the scope concept is applied to both API client and end-user
sessions. When the session is created, we consult the relevant bits of data in
our system (e.g. what roles the user has, what privileges are associated with
those roles) to determine what the user is authorized to do. Those privileges
are attached to the user's session as authorization scopes.

This module simply defines a set of constants (str) that can be used to refer
to specific authorization scopes. Rather than refer to scopes by writing new
str objects, these constants should be imported and used. This improves the
semantics of code, and reduces the risk of programming errors. For an example,
see :mod:`arxiv.users.auth.decorators`.

"""
from typing import Optional


EDIT_PROFILE = 'profile:update'
"""
Authorizes editing user profile.

This includes things like affiliation, full name, etc..
"""

VIEW_PROFILE = 'profile:read'
"""
Authorizes viewing the content of a user profile.

This includes things like affiliation, full name, and e-mail address.
"""

CREATE_SUBMISSION = 'submission:create'
"""Authorizes creating a new submission."""

EDIT_SUBMISSION = 'submission:update'
"""Authorizes updating a submission that has not yet been announced."""

VIEW_SUBMISSION = 'submission:read'
"""Authorizes viewing a submission."""

PROXY_SUBMISSION = 'submission:proxy'
"""
Authorizes creating a submission on behalf of another user.

This authorization is specifically for human users submitting on behalf of
other human users. For client authorization to submit on behalf of a user,
<code>submission:create</code> should be used instead.
"""

READ_UPLOAD = 'upload:read'
"""Authorizes viewing the content of an upload workspace."""

WRITE_UPLOAD = 'upload:write'
"""Authorizes uploading files to to a workspace."""

RELEASE_UPLOAD = 'upload:release'
"""Authorizes releasing an upload workspace."""

ADMIN_UPLOAD = 'upload:admin'
"""Authorizes administrative powers related to uploads."""

GENERAL_USER = [
    EDIT_PROFILE,
    VIEW_PROFILE,
    CREATE_SUBMISSION,
    EDIT_SUBMISSION,
    VIEW_SUBMISSION
]

_HUMAN_LABELS = {
    EDIT_PROFILE: "Grants authorization to change the contents of your user"
                  " profile. This includes your affiliation, preferred name,"
                  " default submission category, etc.",
    VIEW_PROFILE: "Grants authorization to view the contents of your user"
                  " profile. This includes your affiliation, preferred name,"
                  " default submission category, etc.",
    CREATE_SUBMISSION: "Grants authorization to submit papers on your behalf.",
    EDIT_SUBMISSION: "Grants authorization to make changes to your submissions"
                     " that have not yet been announced. For example, to"
                     " update the DOI or journal reference field on your"
                     " behalf. Note that this affects only the metadata of"
                     " your submission, and not the content.",
    READ_UPLOAD: "Grants authorization to view the contents of your uploads.",
    WRITE_UPLOAD: "Grants authorization to add and delete files on your"
                  " behalf.",
}

def get_human_label(scope: str) -> Optional[str]:
    """The the human-readable label for a scope, for display to end users."""
    return _HUMAN_LABELS.get(scope)
