import path from 'path'

export const routes = [
  {
    // Registered here rather than in core/routes.js so the whole Backup section
    // stays inside the fork's own module.
    name: 'admin-backup',
    path: '/admin/backup',
    file: path.resolve(__dirname, 'pages/adminBackup.vue'),
  },
  {
    name: 'arabase-public-dashboard',
    path: '/public/dashboard/:slug',
    file: path.resolve(__dirname, 'pages/publicDashboard.vue'),
  },
  {
    name: 'arabase-public-dashboard-auth',
    path: '/public/dashboard/:slug/auth',
    file: path.resolve(__dirname, 'pages/publicDashboardLogin.vue'),
  },
]
