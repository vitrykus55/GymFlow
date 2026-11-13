"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/lib/api";

type AuthMode = "login" | "register";
type AccessTokenResponse = { access_token: string; token_type: "bearer" };
type CurrentUser = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
};

const fieldClass =
  "mt-1 w-full rounded-lg border border-black/15 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 dark:border-white/20 dark:bg-gray-900 dark:text-white";

export function AuthPanel() {
  const [mode, setMode] = useState<AuthMode>("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [restoring, setRestoring] = useState(true);
  const restoreStarted = useRef(false);

  useEffect(() => {
    if (restoreStarted.current) return;
    restoreStarted.current = true;

    void apiFetch<AccessTokenResponse>("/api/v1/auth/refresh", { method: "POST" })
      .then(async (tokens) => {
        const currentUser = await fetchCurrentUser(tokens.access_token);
        setAccessToken(tokens.access_token);
        setUser(currentUser);
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.message !== "Invalid refresh token.") {
          setMessage(error.message);
        }
      })
      .finally(() => setRestoring(false));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");

    try {
      if (mode === "register") {
        await apiFetch("/api/v1/auth/register", {
          method: "POST",
          body: JSON.stringify({
            email,
            password,
            first_name: firstName,
            last_name: lastName,
            phone: phone || null,
          }),
        });
        setPassword("");
        setMode("login");
        setMessage("Аккаунт создан. Войдите, используя свой email и пароль.");
        return;
      }

      const tokens = await apiFetch<AccessTokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const currentUser = await fetchCurrentUser(tokens.access_token);
      setAccessToken(tokens.access_token);
      setUser(currentUser);
      setPassword("");
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось выполнить запрос.");
    } finally {
      setBusy(false);
    }
  }

  async function handleLogout() {
    setBusy(true);
    setMessage("");
    try {
      await apiFetch<void>("/api/v1/auth/logout", { method: "POST" });
      setUser(null);
      setAccessToken(null);
      setMode("login");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось выйти из аккаунта.");
    } finally {
      setBusy(false);
    }
  }

  if (restoring) {
    return <p className="text-sm text-gray-500">Проверяем сессию...</p>;
  }

  if (user && accessToken) {
    return (
      <section className="w-full max-w-md rounded-2xl border border-black/10 bg-white p-6 shadow-sm dark:border-white/15 dark:bg-gray-950">
        <h2 className="text-xl font-semibold">Вы вошли в GymFlow</h2>
        <p className="mt-3 text-sm text-gray-600 dark:text-gray-300">
          {user.first_name} {user.last_name}
          <br />
          {user.email}
        </p>
        {message && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {message}
          </p>
        )}
        <button
          className="mt-5 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-white dark:text-gray-900"
          disabled={busy}
          onClick={handleLogout}
          type="button"
        >
          Выйти
        </button>
      </section>
    );
  }

  return (
    <section className="w-full max-w-md rounded-2xl border border-black/10 bg-white p-6 shadow-sm dark:border-white/15 dark:bg-gray-950">
      <div className="flex gap-2" aria-label="Вход или регистрация">
        <button
          aria-pressed={mode === "register"}
          className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium ${mode === "register" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200"}`}
          onClick={() => {
            setMode("register");
            setMessage("");
          }}
          type="button"
        >
          Регистрация
        </button>
        <button
          aria-pressed={mode === "login"}
          className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium ${mode === "login" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200"}`}
          onClick={() => {
            setMode("login");
            setMessage("");
          }}
          type="button"
        >
          Вход
        </button>
      </div>

      <h2 className="mt-5 text-xl font-semibold">
        {mode === "register" ? "Создать аккаунт клиента" : "Войти в аккаунт"}
      </h2>

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        {mode === "register" && (
          <>
            <label className="block text-sm font-medium">
              Имя
              <input
                autoComplete="given-name"
                className={fieldClass}
                maxLength={100}
                onChange={(event) => setFirstName(event.target.value)}
                required
                value={firstName}
              />
            </label>
            <label className="block text-sm font-medium">
              Фамилия
              <input
                autoComplete="family-name"
                className={fieldClass}
                maxLength={100}
                onChange={(event) => setLastName(event.target.value)}
                required
                value={lastName}
              />
            </label>
            <label className="block text-sm font-medium">
              Телефон (необязательно)
              <input
                autoComplete="tel"
                className={fieldClass}
                maxLength={30}
                onChange={(event) => setPhone(event.target.value)}
                type="tel"
                value={phone}
              />
            </label>
          </>
        )}
        <label className="block text-sm font-medium">
          Email
          <input
            autoComplete="email"
            className={fieldClass}
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </label>
        <label className="block text-sm font-medium">
          Пароль
          <input
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            className={fieldClass}
            minLength={8}
            maxLength={128}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>

        {message && (
          <p className="text-sm text-blue-700 dark:text-blue-300" role="status">
            {message}
          </p>
        )}

        <button
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={busy}
          type="submit"
        >
          {busy ? "Подождите..." : mode === "register" ? "Зарегистрироваться" : "Войти"}
        </button>
      </form>
    </section>
  );
}

async function fetchCurrentUser(accessToken: string): Promise<CurrentUser> {
  return apiFetch<CurrentUser>("/api/v1/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
