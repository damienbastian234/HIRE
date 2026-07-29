import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Input from "../components/Input";
import Button from "../components/Button";
import useAuth from "../hooks/useAuth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [role, setRole] = useState("candidate");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  const validate = () => {
    const next = {};
    if (form.name.trim().length < 2) next.name = "Enter your full name.";
    if (!/^\S+@\S+\.\S+$/.test(form.email)) next.email = "Enter a valid email address.";
    if (form.password.length < 6) next.password = "Password must be at least 6 characters.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setIsLoading(true);
    // Replace with services/api.js -> register({ ...form, role }) once backend is connected.
    await new Promise((resolve) => setTimeout(resolve, 600));
    signIn(role);
    setIsLoading(false);
    navigate("/dashboard");
  };

  return (
    <div className="container-page flex min-h-[calc(100vh-64px)] items-center justify-center py-16">
      <div className="w-full max-w-sm">
        <span className="eyebrow">Get started</span>
        <h1 className="mt-3 text-2xl font-semibold">Create your account</h1>
        <p className="mt-1.5 text-sm text-slate">Set up a profile to get matched with real openings.</p>

        <div className="mt-6 grid grid-cols-2 gap-2 rounded-full bg-ink/5 p-1">
          {["candidate", "recruiter"].map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setRole(option)}
              className={`rounded-full py-2 text-sm font-medium capitalize transition-colors ${
                role === option ? "bg-white text-ink shadow-card" : "text-slate"
              }`}
            >
              {option}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4" noValidate>
          <Input
            label="Full name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            error={errors.name}
            placeholder="Ananya Rao"
            autoComplete="name"
          />
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
            placeholder="At least 6 characters"
            autoComplete="new-password"
          />
          <Button type="submit" variant="signal" size="lg" isLoading={isLoading} className="mt-2">
            Create account
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-ink hover:text-signal-dark">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
