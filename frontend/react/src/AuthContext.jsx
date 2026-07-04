import { createContext, useContext, useEffect, useState } from "react";

const AuthContext = createContext(null);

const apiBase =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? "/api" : "http://127.0.0.1:5000");

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("ecoguard_token") || "");
  const [username, setUsername] = useState(() => localStorage.getItem("ecoguard_username") || "");
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    async function verify() {
      if (!token) {
        setChecking(false);
        return;
      }
      try {
        const r = await fetch(`${apiBase}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok) {
          setToken("");
          setUsername("");
          localStorage.removeItem("ecoguard_token");
          localStorage.removeItem("ecoguard_username");
        }
      } catch {
        // network hiccup — keep existing token, don't log the user out
      } finally {
        setChecking(false);
      }
    }
    verify();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function login(newToken, newUsername) {
    setToken(newToken);
    setUsername(newUsername);
    localStorage.setItem("ecoguard_token", newToken);
    localStorage.setItem("ecoguard_username", newUsername);
  }

  function logout() {
    setToken("");
    setUsername("");
    localStorage.removeItem("ecoguard_token");
    localStorage.removeItem("ecoguard_username");
  }

  return (
    <AuthContext.Provider value={{ token, username, isLoggedIn: !!token, checking, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export { apiBase };