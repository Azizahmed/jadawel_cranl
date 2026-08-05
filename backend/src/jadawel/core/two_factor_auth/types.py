from typing import NewType

from jadawel.core.two_factor_auth.models import TwoFactorAuthProviderModel

TwoFactorProviderForUpdate = NewType(
    "TwoFactorProviderForUpdate", TwoFactorAuthProviderModel
)
