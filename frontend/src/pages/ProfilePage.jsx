import { useState } from "react";
import Input from "../components/Input";
import Button from "../components/Button";
import ToastContainer from "../components/Toast";
import useToast from "../hooks/useToast";
import { mockUser } from "../services/mockData";

export default function ProfilePage() {
  const [form, setForm] = useState({
    name: mockUser.name,
    title: mockUser.title,
    email: mockUser.email,
    location: mockUser.location,
  });
  const [isSaving, setIsSaving] = useState(false);
  const { toasts, addToast, removeToast } = useToast();

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    // Replace with services/api.js -> updateProfile(form)
    await new Promise((resolve) => setTimeout(resolve, 600));
    setIsSaving(false);
    addToast("Profile updated.", "success");
  };

  return (
    <div className="mx-auto max-w-xl">
      <div className="flex items-center gap-4">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-ink font-display text-lg font-semibold text-signal">
          {mockUser.avatarInitials}
        </span>
        <div>
          <h1 className="text-xl font-semibold">{form.name}</h1>
          <p className="text-sm text-slate">{form.title}</p>
        </div>
      </div>

      <form onSubmit={handleSave} className="mt-8 flex flex-col gap-4">
        <Input label="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <Input label="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <Input
          label="Email"
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <Input label="Location" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
        <Button type="submit" variant="signal" size="lg" isLoading={isSaving} className="mt-2 self-start">
          Save changes
        </Button>
      </form>

      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}
