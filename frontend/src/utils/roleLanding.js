export const normalizeRole = (role) => {
  if (!role) return ''
  return String(role).replace('-', '_')
}

export const getRoleLandingPath = () => '/dashboard'

export const resolveRoleTerminalPath = () => '/dashboard'
