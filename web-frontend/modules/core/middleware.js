import settings from '@jadawel/modules/core/middleware/settings'
import authentication from '@jadawel/modules/core/middleware/authentication'
import authenticated from '@jadawel/modules/core/middleware/authenticated'
import staff from '@jadawel/modules/core/middleware/staff'
import workspacesAndApplications from '@jadawel/modules/core/middleware/workspacesAndApplications'
import pendingJobs from '@jadawel/modules/core/middleware/pendingJobs'
import urlCheck from '@jadawel/modules/core/middleware/urlCheck'
import impersonate from '@jadawel/modules/core/middleware/impersonate'

import Middleware from './middleware'

Middleware.settings = settings
Middleware.authentication = authentication
Middleware.authenticated = authenticated
Middleware.staff = staff
Middleware.workspacesAndApplications = workspacesAndApplications
Middleware.pendingJobs = pendingJobs
Middleware.urlCheck = urlCheck
Middleware.impersonate = impersonate
