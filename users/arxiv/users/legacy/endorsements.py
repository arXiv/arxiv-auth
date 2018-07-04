"""
Provide endorsement authorizations for users.

Endorsements are authorization scopes tied to specific classificatory
categories, and are used primarily to determine whether or not a user may
submit a paper with a particular primary or secondary classification.

This module preserves the behavior of the legacy system with respect to
interpreting endorsements and evaluating potential autoendorsement. The
relevant policies can be found on the `arXiv help pages
<https://arxiv.org/help/endorsement>`_.
"""

from typing import List, Dict, Optional, Callable
from collections import Counter
from datetime import datetime

from sqlalchemy.sql.expression import literal

from . import util
from .. import domain
from arxiv import taxonomy
from .models import DBUser, DBEndorsement, DBPaperOwners, DBDocuments, \
    DBDocumentInCategory, DBCategory, DBEndorsementDomain, DBEmailWhitelist, \
    DBEmailBlacklist


GENERAL_CATEGORIES = [
    domain.Category('math', 'GM'),
    domain.Category('physics', 'gen-ph')
]

WINDOW_START = util.from_epoch(157783680)


def get_endorsements(user: domain.User) -> List[domain.Category]:
    """
    Get all endorsements (explicit and implicit) for a user.

    Parameters
    ----------
    user : :class:`.domain.User`

    Returns
    -------
    list
        Each item is a :class:`.domain.Category` for which the user is
        either explicitly or implicitly endorsed.

    """
    return list(set(explicit_endorsements(user))
                | set(implicit_endorsements(user)))


def explicit_endorsements(user: domain.User) -> List[domain.Category]:
    """
    Load endorsed categories for a user.

    These are endorsements (including auto-endorsements) that have been
    explicitly commemorated.

    Parameters
    ----------
    user : :class:`.domain.User`

    Returns
    -------
    list
        Each item is a :class:`.domain.Category` for which the user is
        explicitly endorsed.
    """
    with util.transaction() as session:
        data: List[DBEndorsement] = (
            session.query(
                DBEndorsement.archive,
                DBEndorsement.subject_class,
                DBEndorsement.point_value,
            )
            .filter(DBEndorsement.endorsee_id == user.user_id)
            .filter(DBEndorsement.flag_valid == 1)
            .all()
        )
    pooled: Counter = Counter()
    for archive, subject, points in data:
        pooled[domain.Category(archive, subject)] += points
    return [category for category, points in pooled.items() if points]


def implicit_endorsements(user: domain.User) -> List[domain.Category]:
    """
    Determine categories for which a user may be autoendorsed.

    In the classic system, this was determined upon request, when the user
    attempted to submit to a particular category. Because we are separating
    authorization concerns (which includes endorsement) from the submission
    system itself, we want to calculate possible autoendorsement categories
    ahead of time.

    New development of autoendorsement-related functionality should not happen
    here. This function and related code are intended only to preserve the
    business logic already implemented in the classic system.

    Parameters
    ----------
    :class:`.User`

    Returns
    -------
    list
        Each item is a :class:`.domain.Category` for which the user may be
        auto-endorsed.
    """
    candidates = [domain.Category.from_compound(category)
                  for category, data in taxonomy.CATEGORIES_ACTIVE.items()]
    policies = category_policies()
    invalidated = invalidated_autoendorsements(user)
    papers = domain_papers(user)
    user_is_academic = is_academic(user)
    return [
        category for category in candidates
        if category in policies
        and not _disqualifying_invalidations(category, invalidated)
        and (policies[category]['endorse_all']
             or _endorse_by_email(category, policies, user_is_academic)
             or _endorse_by_papers(category, policies, papers))
    ]


def is_academic(user: domain.User) -> bool:
    """
    Determine whether a user is academic, based on their email address.

    Uses whitelist and blacklist patterns in the database.

    Parameters
    ----------
    user : :class:`.domain.User`

    Returns
    -------
    bool
    """
    with util.transaction() as session:
        in_whitelist = (
            session.query(DBEmailWhitelist)
            .filter(literal(user.email).like(DBEmailWhitelist.pattern))
            .first()
        )
        if in_whitelist:
            return True
        in_blacklist = (
            session.query(DBEmailBlacklist)
            .filter(literal(user.email).like(DBEmailBlacklist.pattern))
            .first()
        )
        if in_blacklist:
            return False
    return True


def _disqualifying_invalidations(category: domain.Category,
                                 invalidated: List[domain.Category]) -> bool:
    """
    Evaluate whether endorsement invalidations are disqualifying.

    This enforces the policy that invalidated (revoked) auto-endorsements can
    prevent future auto-endorsement.

    Parameters
    ----------
    category : :class:`.Category`
        The category for which an auto-endorsement is being considered.
    invalidated : list
        Categories for which the user has had auto-endorsements invalidated
        (revoked).

    Returns
    -------
    bool
    """
    return bool((category in GENERAL_CATEGORIES and category in invalidated)
                or (category not in GENERAL_CATEGORIES and invalidated))


def _endorse_by_email(category: domain.Category,
                      policies: Dict[domain.Category, Dict],
                      user_is_academic: bool) -> bool:
    """
    Evaluate whether an auto-endorsement can be issued based on email address.

    This enforces the policy that some categories allow auto-endorsement for
    academic users.

    Parameters
    ----------
    category : :class:`.Category`
        The category for which an auto-endorsement is being considered.
    policies : dict
        Describes auto-endorsement policies for each category (inherited from
        their endorsement domains).
    user_is_academic : bool
        Whether or not the user has been determined to be academic.

    Returns
    -------
    bool
    """
    policy = policies.get(category)
    if policy is None or 'endorse_email' not in policy:
        return False
    return policy['endorse_email'] and user_is_academic


def _endorse_by_papers(category: domain.Category,
                       policies: Dict[domain.Category, Dict],
                       papers: Dict[str, int]) -> bool:
    """
    Evaluate whether an auto-endorsement can be issued based on prior papers.

    This enforces the policy that some categories allow auto-endorsements for
    users who have published a minimum number of papers in categories that
    share an endoresement domain.

    Parameters
    ----------
    category : :class:`.Category`
        The category for which an auto-endorsement is being considered.
    policies : dict
        Describes auto-endorsement policies for each category (inherited from
        their endorsement domains).
    papers : dict
        The number of papers that the user has published in each endorsement
        domain. Keys are str names of endorsement domains, values are int.

    Returns
    -------
    bool
    """
    N_papers = papers[policies[category]['domain']]
    min_papers = policies[category]['min_papers']
    return bool(N_papers >= min_papers)


def domain_papers(user: domain.User,
                  start_date: Optional[datetime] = None) -> Dict[str, int]:
    """
    Calculate the number of papers that a user owns in each endorsement domain.

    This includes both submitted and claimed papers.

    Parameters
    ----------
    user : :class:`.domain.User`
    start_date : :class:`.datetime` or None
        If provided, will only count papers published after this date.

    Returns
    -------
    dict
        Keys are classification domains (str), values are the number of papers
        in each respective domain (int).

    """
    with util.transaction() as session:
        query = (
            session.query(
                DBPaperOwners.document_id,
                DBDocuments.document_id,
                DBDocumentInCategory.document_id,
                DBCategory.endorsement_domain
            )
            .filter(DBPaperOwners.user_id == user.user_id)
            # Lots of joins...
            .filter(DBDocuments.document_id == DBPaperOwners.document_id)
            .filter(
                DBDocumentInCategory.document_id == DBDocuments.document_id
            )
            .filter(DBCategory.archive == DBDocumentInCategory.archive)
            .filter(
                DBCategory.subject_class == DBDocumentInCategory.subject_class
            )
        )
        if start_date:
            query = query.filter(DBDocuments.dated > util.epoch(start_date))
        data = query.all()
    return dict(Counter(domain for _, _, _, domain in data).items())


def category_policies() -> Dict[domain.Category, Dict]:
    """
    Load auto-endorsement policies for each category from the database.

    Each category belongs to an endorsement domain, which defines the
    auto-endorsement policies. We retrieve those policies from the perspective
    of the individueal category for ease of lookup.

    Returns
    -------
    dict
        Keys are :class:`.domain.Category` instances. Values are dicts with
        policiy details.

    """
    with util.transaction() as session:
        data = (
            session.query(
                DBCategory.archive,
                DBCategory.subject_class,
                DBEndorsementDomain.endorse_all,
                DBEndorsementDomain.endorse_email,
                DBEndorsementDomain.papers_to_endorse,
                DBEndorsementDomain.endorsement_domain
            )
            .filter(DBCategory.definitive == 1)
            .filter(DBCategory.active == 1)
            .filter(DBCategory.endorsement_domain ==
                    DBEndorsementDomain.endorsement_domain)
            .all()
        )
    return {
        domain.Category(archive, subject): {
            'domain': e_domain,
            'endorse_all': endorse_all == 'y',
            'endorse_email': endorse_email == 'y',
            'min_papers': min_papers
        }
        for archive, subject, endorse_all, endorse_email, min_papers, e_domain
        in data
    }


def invalidated_autoendorsements(user: domain.User) -> List[domain.Category]:
    """
    Load any invalidated (revoked) auto-endorsements for a user.

    Parameters
    ----------
    user : :class:`.domain.User`

    Returns
    -------
    list
        Items are :class:`.domain.Category` for which the user has had past
        auto-endorsements revoked.
    """
    with util.transaction() as session:
        data: List[DBEndorsement] = (
            session.query(
                DBEndorsement.archive,
                DBEndorsement.subject_class
            )
            .filter(DBEndorsement.endorsee_id == user.user_id)
            .filter(DBEndorsement.flag_valid == 0)
            .filter(DBEndorsement.endorsement_type == 'auto')
            .all()
        )
    return [domain.Category(archive, subject) for archive, subject in data]
