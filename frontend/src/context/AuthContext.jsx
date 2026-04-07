import React, { createContext, useContext, useState, useCallback } from 'react'

const AuthContext = createContext(null)

const TOKEN_KEY = 'golfplanner_token'
const USER_KEY = 'golfplanner_user'

function safeStorageGet(key) {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function safeStorageSet(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Ignore storage write failures so the app can still render and function in-memory.
  }
}

function safeStorageRemove(key) {
  try {
    window.localStorage.removeItem(key)
  } catch {
    // Ignore storage removal failures.
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => safeStorageGet(TOKEN_KEY) || null)
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(safeStorageGet(USER_KEY) || 'null')
    } catch {
      return null
    }
  })

  const login = useCallback((tokenValue, userData) => {
    safeStorageSet(TOKEN_KEY, tokenValue)
    safeStorageSet(USER_KEY, JSON.stringify(userData))
    setToken(tokenValue)
    setUser(userData)
  }, [])

  const logout = useCallback(() => {
    safeStorageRemove(TOKEN_KEY)
    safeStorageRemove(USER_KEY)
    setToken(null)
    setUser(null)
  }, [])

  /** Attach Authorization header to any fetch options object. */
  const authHeaders = useCallback(() => ({
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }), [token])

  return (
    <AuthContext.Provider value={{ token, user, login, logout, authHeaders, isLoggedIn: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
