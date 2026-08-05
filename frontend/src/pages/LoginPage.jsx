import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Input from "../components/Input";
import Button from "../components/Button";
import useAuth from "../hooks/useAuth";
import { login, getProfile } from "../services/api";

export default function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState("");

  const validate = () => {
    const next = {};
    if (!/^\S+@\S+\.\S+$/.test(form.email)) next.email = "Enter a valid email address.";
    if (form.password.length < 6) next.password = "Password must be at least 6 characters.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setIsLoading(true);
    setServerError("");
    try {
      const { data } = await login(form);
      signIn(data.user, data.token);
      
      // Fetch the latest profile to ensure we have up-to-date user data
      try {
        const { data: profileData } = await getProfile();
        const latestProfile = profileData.profile || profileData;
        signIn({
          ...data.user,
          name: latestProfile.name,
          title: latestProfile.title,
          email: latestProfile.email,
          location: latestProfile.location,
        }, data.token);
      } catch (profileError) {
        // If fetching profile fails, continue with the login data we have
        console.warn("Failed to fetch latest profile:", profileError);
      }
      
      navigate("/dashboard");
    } catch (error) {
      setServerError(error.response?.data?.detail || "Unable to sign in right now.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container-page flex min-h-[calc(100vh-64px)] items-center justify-center py-16">
      <div className="w-full max-w-sm">
        <span className="eyebrow">Welcome back</span>
        <h1 className="mt-3 text-2xl font-semibold">Sign in to H.I.R.E.</h1>
        <p className="mt-1.5 text-sm text-slate">Track applications and pick up where you left off.</p>

        <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4" noValidate>
          <Input
            label="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            error={errors.email}
            placeholder="you@example.com"
            autoComplete="email"
          />
          <Input
            label="Password"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            error={errors.password}
            placeholder="••••••••"
            autoComplete="current-password"
          />
          {serverError ? <p className="text-sm text-alert">{serverError}</p> : null}
          <Button type="submit" variant="signal" size="lg" isLoading={isLoading} className="mt-2">
            Sign in
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate">
          New to H.I.R.E.?{" "}
          <Link to="/register" className="font-medium text-ink hover:text-signal-dark">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
