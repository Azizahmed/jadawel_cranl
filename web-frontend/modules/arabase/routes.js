import path from 'path'

export const routes = [
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
